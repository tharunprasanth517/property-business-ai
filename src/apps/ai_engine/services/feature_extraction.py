"""
feature_extraction.py — Convert raw ORM data into structured feature vectors.

This module is the bridge between the existing Phase 1–5 data models and the
ai_engine intelligence layer.  It converts ORM querysets into the typed DTOs
defined in contracts.py without adding any intelligence of its own.

Each extractor function:
  - Accepts a tenant-verified context object (BusinessContext or PropertyContext)
    so tenant isolation is enforced before this layer runs.
  - Returns the corresponding DTO (PropertyFeatures or BusinessFeatures).
  - Uses Decimal for all monetary values — no float conversion.
  - Handles missing / None data gracefully (None in DTO, not exception).
  - Never calls the ORM directly with arbitrary IDs; always starts from the
    context's confirmed ORM objects.

No intelligence, scoring, or prediction is performed here.
"""

from __future__ import annotations

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional

from django.db.models import Count, Q, Sum

from apps.businesses.models import Property
from apps.finances.models import LoanPayment, PropertyExpense, PropertyLoan
from apps.inventory.models import StockLevel
from apps.products.models import Product
from apps.transactions.models import BusinessExpense, Purchase, Sale

from .contracts import BusinessFeatures, PropertyFeatures
from .context import BusinessContext, PropertyContext


ZERO = Decimal("0.00")

# ---------------------------------------------------------------------------
# Property feature extraction
# ---------------------------------------------------------------------------


def extract_property_features(ctx: PropertyContext) -> PropertyFeatures:
    """
    Extract a complete PropertyFeatures vector for a single verified property.

    Args:
        ctx: A PropertyContext returned by context.get_property_context().
             Must already be tenant-verified; this function trusts ctx.

    Returns:
        PropertyFeatures dataclass with all available fields populated.
        Fields that cannot be computed (e.g. missing purchase_price) are None.
    """
    prop = ctx.property
    business = ctx.business

    # ------------------------------------------------------------------ #
    # Expenses                                                             #
    # ------------------------------------------------------------------ #
    expenses_qs = PropertyExpense.objects.filter(
        business=business, property=prop
    )
    expense_agg = expenses_qs.aggregate(
        total=Sum("amount"),
        count=Count("id"),
    )
    total_expenses: Optional[Decimal] = expense_agg["total"]
    expense_count: int = expense_agg["count"] or 0

    # ------------------------------------------------------------------ #
    # Loans                                                                #
    # ------------------------------------------------------------------ #
    loans_qs = PropertyLoan.objects.filter(business=business, property=prop)
    loan_agg = loans_qs.aggregate(
        total_principal=Sum("principal_amount"),
        total_outstanding=Sum("outstanding_balance"),
        loan_count=Count("id"),
    )
    active_loan_agg = loans_qs.filter(is_active=True).aggregate(
        active_count=Count("id"),
        active_outstanding=Sum("outstanding_balance"),
    )
    total_loan_principal: Optional[Decimal] = loan_agg["total_principal"]
    outstanding_loan_balance: Optional[Decimal] = active_loan_agg["active_outstanding"]
    loan_count: int = loan_agg["loan_count"] or 0
    active_loan_count: int = active_loan_agg["active_count"] or 0

    # Payments
    payments_qs = LoanPayment.objects.filter(
        business=business, loan__property=prop
    )
    payment_agg = payments_qs.aggregate(
        total_interest=Sum("interest_paid"),
        total_principal=Sum("principal_paid"),
    )
    total_interest_paid: Optional[Decimal] = payment_agg["total_interest"]

    # ------------------------------------------------------------------ #
    # Total invested (purchase + expenses + interest)                     #
    # ------------------------------------------------------------------ #
    purchase_price = prop.purchase_price  # may be None

    total_invested: Optional[Decimal] = None
    if purchase_price is not None:
        total_invested = (
            purchase_price
            + (total_expenses or ZERO)
            + (total_interest_paid or ZERO)
        )

    # ------------------------------------------------------------------ #
    # Return on investment                                                 #
    # ------------------------------------------------------------------ #
    current_estimated_value = prop.current_estimated_value
    expected_selling_price = prop.expected_selling_price

    current_roi_pct: Optional[Decimal] = None
    potential_roi_pct: Optional[Decimal] = None

    if total_invested and total_invested > ZERO:
        if current_estimated_value is not None:
            current_pnl = current_estimated_value - total_invested
            current_roi_pct = (current_pnl / total_invested * 100).quantize(
                Decimal("0.01")
            )
        if expected_selling_price is not None:
            potential_pnl = expected_selling_price - total_invested
            potential_roi_pct = (potential_pnl / total_invested * 100).quantize(
                Decimal("0.01")
            )

    # ------------------------------------------------------------------ #
    # Loan-to-value ratio (outstanding / current_estimated_value)         #
    # ------------------------------------------------------------------ #
    loan_to_value_ratio: Optional[Decimal] = None
    if (
        outstanding_loan_balance is not None
        and current_estimated_value is not None
        and current_estimated_value > ZERO
    ):
        loan_to_value_ratio = (
            outstanding_loan_balance / current_estimated_value * 100
        ).quantize(Decimal("0.01"))

    # ------------------------------------------------------------------ #
    # Days held                                                            #
    # ------------------------------------------------------------------ #
    days_held: Optional[int] = None
    if prop.purchase_date is not None:
        days_held = (date.today() - prop.purchase_date).days

    return PropertyFeatures(
        property_id=prop.pk,
        business_id=business.pk,
        property_name=prop.name,
        property_type=prop.property_type,
        ownership_status=prop.ownership_status,
        development_status=prop.development_status,
        area=prop.area,
        area_unit=prop.area_unit,
        purchase_price=purchase_price,
        current_estimated_value=current_estimated_value,
        expected_selling_price=expected_selling_price,
        total_expenses=total_expenses,
        total_loan_principal=total_loan_principal,
        outstanding_loan_balance=outstanding_loan_balance,
        total_interest_paid=total_interest_paid,
        total_invested=total_invested,
        current_roi_pct=current_roi_pct,
        potential_roi_pct=potential_roi_pct,
        loan_to_value_ratio=loan_to_value_ratio,
        purchase_date=prop.purchase_date,
        days_held=days_held,
        expense_count=expense_count,
        loan_count=loan_count,
        active_loan_count=active_loan_count,
    )


# ---------------------------------------------------------------------------
# Business feature extraction
# ---------------------------------------------------------------------------


def extract_business_features(
    ctx: BusinessContext,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> BusinessFeatures:
    """
    Extract a complete BusinessFeatures vector for a verified business.

    Args:
        ctx:       A BusinessContext returned by context.get_business_context().
        date_from: Optional start of the date range (inclusive).
        date_to:   Optional end of the date range (inclusive).

    Returns:
        BusinessFeatures dataclass with all available fields populated.
        Fields that cannot be computed (e.g. no transactions) are None.
    """
    business = ctx.business

    # ------------------------------------------------------------------ #
    # Transaction querysets (tenant-scoped by business FK)                #
    # ------------------------------------------------------------------ #
    # Expense model distinction (important for Step 2 rule writers):
    #
    #   BusinessExpense  (apps.transactions)  — operational overhead that has
    #     nothing to do with properties: marketing, salaries, software, utilities.
    #     One record can only ever appear in this table.
    #
    #   PropertyExpense  (apps.finances)  — costs tracked against a specific
    #     property (maintenance, renovation, stamp duty …) OR, when property=None,
    #     business-level property-related overhead (shared-office electricity,
    #     accountant fees, etc.).
    #
    # These are two separate database tables.  A cost is entered into ONE of
    # them depending on its nature — there is no overlap and no double-counting.
    # This four-queryset structure is identical to the canonical Phase 5
    # business_finance_service.get_business_pl_summary(), which is the
    # authoritative reference for the P&L calculation.
    sales_qs = Sale.objects.filter(business=business)
    purchases_qs = Purchase.objects.filter(business=business)
    biz_expenses_qs = BusinessExpense.objects.filter(business=business)
    prop_overhead_qs = PropertyExpense.objects.filter(
        business=business, property__isnull=True
    )

    if date_from:
        sales_qs = sales_qs.filter(sale_date__gte=date_from)
        purchases_qs = purchases_qs.filter(purchase_date__gte=date_from)
        biz_expenses_qs = biz_expenses_qs.filter(expense_date__gte=date_from)
        prop_overhead_qs = prop_overhead_qs.filter(expense_date__gte=date_from)

    if date_to:
        sales_qs = sales_qs.filter(sale_date__lte=date_to)
        purchases_qs = purchases_qs.filter(purchase_date__lte=date_to)
        biz_expenses_qs = biz_expenses_qs.filter(expense_date__lte=date_to)
        prop_overhead_qs = prop_overhead_qs.filter(expense_date__lte=date_to)

    # ------------------------------------------------------------------ #
    # P&L aggregates                                                       #
    # ------------------------------------------------------------------ #
    revenue: Optional[Decimal] = (
        sales_qs.aggregate(t=Sum("total_amount"))["t"]
    )
    cogs: Optional[Decimal] = (
        purchases_qs.aggregate(t=Sum("total_amount"))["t"]
    )
    operating_expenses: Optional[Decimal] = (
        biz_expenses_qs.aggregate(t=Sum("amount"))["t"]
    )
    property_overhead: Optional[Decimal] = (
        prop_overhead_qs.aggregate(t=Sum("amount"))["t"]
    )

    gross_profit: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    if revenue is not None or cogs is not None:
        gross_profit = (revenue or ZERO) - (cogs or ZERO)
        net_profit = gross_profit - (operating_expenses or ZERO) - (
            property_overhead or ZERO
        )

    # ------------------------------------------------------------------ #
    # Margin / ratio signals                                               #
    # ------------------------------------------------------------------ #
    gross_margin_pct: Optional[Decimal] = None
    net_margin_pct: Optional[Decimal] = None
    expense_ratio_pct: Optional[Decimal] = None

    if revenue and revenue > ZERO:
        if gross_profit is not None:
            gross_margin_pct = (gross_profit / revenue * 100).quantize(
                Decimal("0.01")
            )
        if net_profit is not None:
            net_margin_pct = (net_profit / revenue * 100).quantize(
                Decimal("0.01")
            )
        if operating_expenses is not None:
            expense_ratio_pct = (
                operating_expenses / revenue * 100
            ).quantize(Decimal("0.01"))

    # ------------------------------------------------------------------ #
    # Portfolio aggregates                                                 #
    # ------------------------------------------------------------------ #
    properties_qs = Property.objects.filter(business=business)
    property_count: int = properties_qs.count()

    portfolio_agg = properties_qs.aggregate(
        total_value=Sum("current_estimated_value"),
    )
    total_portfolio_value: Optional[Decimal] = portfolio_agg["total_value"]

    total_outstanding_loans: Optional[Decimal] = (
        PropertyLoan.objects.filter(business=business, is_active=True)
        .aggregate(t=Sum("outstanding_balance"))["t"]
    )

    # ------------------------------------------------------------------ #
    # Inventory / product signals                                          #
    # ------------------------------------------------------------------ #
    products_qs = Product.objects.filter(business=business, is_active=True)
    product_count: int = products_qs.count()

    # Low-stock: StockLevel.quantity <= Product.reorder_level
    # We join StockLevel → Product and filter in the DB.
    low_stock_count: int = (
        StockLevel.objects.filter(business=business)
        .filter(quantity__lte=models_reorder_level_ref())
        .count()
    )

    total_stock_value: Optional[Decimal] = _compute_stock_value(business)

    # ------------------------------------------------------------------ #
    # Temporal signals                                                     #
    # ------------------------------------------------------------------ #
    transaction_days: int = _count_distinct_transaction_days(
        sales_qs, purchases_qs, biz_expenses_qs
    )

    return BusinessFeatures(
        business_id=business.pk,
        business_name=business.name,
        revenue=revenue,
        cogs=cogs,
        gross_profit=gross_profit,
        operating_expenses=operating_expenses,
        property_overhead=property_overhead,
        net_profit=net_profit,
        gross_margin_pct=gross_margin_pct,
        net_margin_pct=net_margin_pct,
        expense_ratio_pct=expense_ratio_pct,
        property_count=property_count,
        total_portfolio_value=total_portfolio_value,
        total_outstanding_loans=total_outstanding_loans,
        product_count=product_count,
        low_stock_product_count=low_stock_count,
        total_stock_value=total_stock_value,
        date_from=date_from,
        date_to=date_to,
        transaction_days=transaction_days,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def models_reorder_level_ref():
    """
    Return a queryset annotation reference for StockLevel low-stock filtering.

    StockLevel.quantity <= Product.reorder_level is expressed as an ORM
    filter using __lte and a subquery alias via .filter(quantity__lte=...).
    We use a raw F() expression so this is computed in-database.
    """
    from django.db.models import F

    return F("product__reorder_level")


def _compute_stock_value(business) -> Optional[Decimal]:
    """
    Compute total stock value (sum of qty * cost_price) for active products.

    Returns None if no products or no cost prices are available.
    Uses Python-level arithmetic to avoid database-specific DECIMAL * INTEGER
    edge cases across MySQL versions.
    """
    stock_levels = (
        StockLevel.objects.filter(business=business)
        .select_related("product")
        .filter(product__is_active=True)
    )

    total = ZERO
    has_data = False
    for sl in stock_levels:
        if sl.product.cost_price is not None and sl.quantity > 0:
            total += sl.product.cost_price * sl.quantity
            has_data = True

    return total if has_data else None


def _count_distinct_transaction_days(
    sales_qs, purchases_qs, biz_expenses_qs
) -> int:
    """
    Count the number of distinct calendar days on which any transaction occurred.

    This is used as a data-richness signal (low count → insufficient data for ML).
    """
    sale_dates = set(
        sales_qs.values_list("sale_date", flat=True).distinct()
    )
    purchase_dates = set(
        purchases_qs.values_list("purchase_date", flat=True).distinct()
    )
    expense_dates = set(
        biz_expenses_qs.values_list("expense_date", flat=True).distinct()
    )
    return len(sale_dates | purchase_dates | expense_dates)
