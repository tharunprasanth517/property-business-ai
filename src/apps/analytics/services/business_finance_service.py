"""
Business-level P&L summary service.

Aggregates across:
  - Sales         → Revenue
  - Purchases     → Cost of Goods Sold (COGS)
  - BusinessExpense → Operating Expenses
  - PropertyExpense (business-level, property=None) → Property Overhead

No Pandas in Phase 5 — pure ORM aggregation.
Monthly trend data (for Chart.js) is built with Python groupby.
"""

from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from apps.finances.models import PropertyExpense
from apps.transactions.models import BusinessExpense, Purchase, Sale


def get_business_pl_summary(business, date_from=None, date_to=None):
    """
    Compute business-level P&L for the given date range.

    Args:
        business:   businesses.Business instance
        date_from:  datetime.date or None (no lower bound)
        date_to:    datetime.date or None (no upper bound)

    Returns:
        dict with revenue, cogs, gross_profit, operating_expenses,
        property_overhead, net_profit, monthly_revenue, monthly_expenses
    """
    ZERO = Decimal("0.00")

    # --- Base querysets ---
    sales_qs = Sale.objects.filter(business=business)
    purchases_qs = Purchase.objects.filter(business=business)
    biz_expenses_qs = BusinessExpense.objects.filter(business=business)
    prop_overhead_qs = PropertyExpense.objects.filter(business=business, property__isnull=True)

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

    # --- Aggregates ---
    revenue = sales_qs.aggregate(total=Sum("total_amount"))["total"] or ZERO
    cogs = purchases_qs.aggregate(total=Sum("total_amount"))["total"] or ZERO
    operating_expenses = biz_expenses_qs.aggregate(total=Sum("amount"))["total"] or ZERO
    property_overhead = prop_overhead_qs.aggregate(total=Sum("amount"))["total"] or ZERO

    gross_profit = revenue - cogs
    net_profit = gross_profit - operating_expenses - property_overhead

    # --- Monthly revenue (for Chart.js bar chart) ---
    monthly_revenue: dict = defaultdict(lambda: ZERO)
    for sale in sales_qs.only("sale_date", "total_amount"):
        key = sale.sale_date.strftime("%Y-%m")
        monthly_revenue[key] += sale.total_amount

    # --- Monthly expenses (COGS + opex combined, for Chart.js) ---
    monthly_expenses: dict = defaultdict(lambda: ZERO)
    for purchase in purchases_qs.only("purchase_date", "total_amount"):
        key = purchase.purchase_date.strftime("%Y-%m")
        monthly_expenses[key] += purchase.total_amount
    for expense in biz_expenses_qs.only("expense_date", "amount"):
        key = expense.expense_date.strftime("%Y-%m")
        monthly_expenses[key] += expense.amount

    # Combine into sorted label list
    all_months = sorted(set(monthly_revenue) | set(monthly_expenses))
    chart_labels = all_months
    chart_revenue = [float(monthly_revenue.get(m, ZERO)) for m in all_months]
    chart_expenses = [float(monthly_expenses.get(m, ZERO)) for m in all_months]

    return {
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "operating_expenses": operating_expenses,
        "property_overhead": property_overhead,
        "net_profit": net_profit,
        "chart_labels": chart_labels,
        "chart_revenue": chart_revenue,
        "chart_expenses": chart_expenses,
        "date_from": date_from,
        "date_to": date_to,
    }
