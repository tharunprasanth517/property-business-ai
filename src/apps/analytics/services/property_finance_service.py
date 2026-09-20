"""
Per-property financial summary service.

Returns a structured dict that views pass directly to templates.
All monetary values are Decimal; callers should format for display.

No Pandas required for Phase 5 — pure ORM aggregation.
Pandas DataFrames will be introduced in Phase 6 for trend analysis.
"""

from decimal import Decimal

from django.db.models import Sum

from apps.finances.models import LoanPayment, PropertyExpense, PropertyLoan, PropertyTransaction


def get_property_financial_summary(property_obj, business):
    """
    Compute and return a complete financial summary for a single property.

    Args:
        property_obj: businesses.Property instance
        business:     businesses.Business instance (tenant)

    Returns:
        dict with the following keys:
          purchase_price, total_expenses, total_expenses_by_category,
          total_loan_principal, total_loan_interest_paid, total_principal_paid,
          outstanding_loan_balance, total_invested, current_estimated_value,
          current_pnl, current_roi_pct, expected_selling_price, potential_pnl,
          potential_roi_pct, recent_expenses, active_loans
    """
    ZERO = Decimal("0.00")

    # --- Purchase price (from Property model field) ---
    purchase_price = property_obj.purchase_price or ZERO

    # --- Expenses ---
    expenses_qs = PropertyExpense.objects.filter(business=business, property=property_obj)
    total_expenses_agg = expenses_qs.aggregate(total=Sum("amount"))
    total_expenses = total_expenses_agg["total"] or ZERO

    # Expenses grouped by category name
    total_expenses_by_category = {}
    for expense in expenses_qs.select_related("category"):
        cat_name = expense.category.name if expense.category else "Uncategorised"
        total_expenses_by_category[cat_name] = (
            total_expenses_by_category.get(cat_name, ZERO) + expense.amount
        )

    # --- Capital transactions ---
    capital_txns = PropertyTransaction.objects.filter(business=business, property=property_obj)

    # --- Loans ---
    loans_qs = PropertyLoan.objects.filter(business=business, property=property_obj)
    total_loan_principal = loans_qs.aggregate(total=Sum("principal_amount"))["total"] or ZERO
    outstanding_loan_balance = loans_qs.filter(is_active=True).aggregate(
        total=Sum("outstanding_balance")
    )["total"] or ZERO

    # Payments made across all loans for this property
    loan_payments_qs = LoanPayment.objects.filter(
        business=business, loan__property=property_obj
    )
    total_interest_paid = loan_payments_qs.aggregate(total=Sum("interest_paid"))["total"] or ZERO
    total_principal_paid = loan_payments_qs.aggregate(total=Sum("principal_paid"))["total"] or ZERO

    # --- Total invested ---
    # purchase_price + all expenses + all interest paid (cost of borrowing)
    total_invested = purchase_price + total_expenses + total_interest_paid

    # --- Current P&L ---
    current_estimated_value = property_obj.current_estimated_value or ZERO
    current_pnl = current_estimated_value - total_invested
    current_roi_pct = ZERO
    if total_invested > 0:
        current_roi_pct = (current_pnl / total_invested * 100).quantize(Decimal("0.01"))

    # --- Potential P&L (vs expected selling price) ---
    expected_selling_price = property_obj.expected_selling_price or ZERO
    potential_pnl = expected_selling_price - total_invested
    potential_roi_pct = ZERO
    if total_invested > 0:
        potential_roi_pct = (potential_pnl / total_invested * 100).quantize(Decimal("0.01"))

    # --- Recent expenses (for display in property detail) ---
    recent_expenses = list(
        expenses_qs.select_related("category").order_by("-expense_date")[:5]
    )

    # --- Active loans (for display in property detail) ---
    active_loans = list(loans_qs.filter(is_active=True))

    return {
        "purchase_price": purchase_price,
        "total_expenses": total_expenses,
        "total_expenses_by_category": total_expenses_by_category,
        "total_loan_principal": total_loan_principal,
        "total_interest_paid": total_interest_paid,
        "total_principal_paid": total_principal_paid,
        "outstanding_loan_balance": outstanding_loan_balance,
        "total_invested": total_invested,
        "current_estimated_value": current_estimated_value,
        "current_pnl": current_pnl,
        "current_roi_pct": current_roi_pct,
        "expected_selling_price": expected_selling_price,
        "potential_pnl": potential_pnl,
        "potential_roi_pct": potential_roi_pct,
        "recent_expenses": recent_expenses,
        "active_loans": active_loans,
        "capital_transactions": list(capital_txns.order_by("-transaction_date")[:5]),
    }
