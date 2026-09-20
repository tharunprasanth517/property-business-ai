"""
Portfolio-level summary service.

Aggregates all properties within a business to provide a cross-property
financial view: total equity, total investment, outstanding loans, and
per-property breakdown for Chart.js donut.
"""

from decimal import Decimal

from django.db.models import Sum

from apps.businesses.models import Property
from apps.finances.models import PropertyExpense, PropertyLoan


def get_portfolio_summary(business):
    """
    Compute a cross-property financial summary for the given business.

    Args:
        business: businesses.Business instance

    Returns:
        dict with portfolio-level totals and per-property breakdown list.
    """
    ZERO = Decimal("0.00")

    properties = Property.objects.filter(business=business)

    total_purchase_cost = properties.aggregate(total=Sum("purchase_price"))["total"] or ZERO
    total_estimated_value = properties.aggregate(total=Sum("current_estimated_value"))["total"] or ZERO
    total_expected_value = properties.aggregate(total=Sum("expected_selling_price"))["total"] or ZERO

    total_expenses = (
        PropertyExpense.objects.filter(business=business, property__isnull=False)
        .aggregate(total=Sum("amount"))["total"] or ZERO
    )

    total_outstanding_loans = (
        PropertyLoan.objects.filter(business=business, is_active=True)
        .aggregate(total=Sum("outstanding_balance"))["total"] or ZERO
    )

    # Net equity: current value − purchase cost − outstanding loans − expenses
    net_equity = total_estimated_value - total_purchase_cost - total_outstanding_loans - total_expenses
    current_portfolio_pnl = total_estimated_value - total_purchase_cost - total_expenses

    # Per-property breakdown (for donut chart)
    property_breakdown = []
    for prop in properties:
        prop_expenses = (
            PropertyExpense.objects.filter(business=business, property=prop)
            .aggregate(total=Sum("amount"))["total"] or ZERO
        )
        prop_loans = (
            PropertyLoan.objects.filter(business=business, property=prop, is_active=True)
            .aggregate(total=Sum("outstanding_balance"))["total"] or ZERO
        )
        invested = (prop.purchase_price or ZERO) + prop_expenses
        current_val = prop.current_estimated_value or ZERO
        pnl = current_val - invested

        property_breakdown.append({
            "property": prop,
            "purchase_price": prop.purchase_price or ZERO,
            "total_expenses": prop_expenses,
            "outstanding_loans": prop_loans,
            "invested": invested,
            "current_value": current_val,
            "pnl": pnl,
        })

    # Chart.js donut data (investment by property)
    chart_labels = [p["property"].name for p in property_breakdown]
    chart_invested = [float(p["invested"]) for p in property_breakdown]

    return {
        "total_purchase_cost": total_purchase_cost,
        "total_estimated_value": total_estimated_value,
        "total_expected_value": total_expected_value,
        "total_expenses": total_expenses,
        "total_outstanding_loans": total_outstanding_loans,
        "net_equity": net_equity,
        "current_portfolio_pnl": current_portfolio_pnl,
        "property_breakdown": property_breakdown,
        "property_count": properties.count(),
        "chart_labels": chart_labels,
        "chart_invested": chart_invested,
    }
