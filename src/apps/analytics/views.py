"""Analytics views — business P&L dashboard and property portfolio summary."""

import json
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.businesses.views import get_active_business

from .services.business_finance_service import get_business_pl_summary
from .services.portfolio_service import get_portfolio_summary


@login_required
def business_dashboard(request):
    """
    Business-level P&L dashboard.
    Optional GET params: date_from, date_to (YYYY-MM-DD).
    """
    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    # Date range filter from GET params
    date_from = None
    date_to = None
    try:
        if request.GET.get("date_from"):
            date_from = date.fromisoformat(request.GET["date_from"])
        if request.GET.get("date_to"):
            date_to = date.fromisoformat(request.GET["date_to"])
    except ValueError:
        pass

    summary = get_business_pl_summary(business, date_from=date_from, date_to=date_to)

    # Serialise chart data for Chart.js (safe JSON in template)
    chart_data = {
        "labels": summary["chart_labels"],
        "revenue": summary["chart_revenue"],
        "expenses": summary["chart_expenses"],
    }

    return render(
        request,
        "analytics/business_dashboard.html",
        {
            "business": business,
            "summary": summary,
            "chart_data_json": json.dumps(chart_data),
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@login_required
def portfolio_summary(request):
    """Cross-property portfolio overview for the active business."""
    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    summary = get_portfolio_summary(business)

    donut_data = {
        "labels": summary["chart_labels"],
        "invested": summary["chart_invested"],
    }

    return render(
        request,
        "analytics/portfolio_summary.html",
        {
            "business": business,
            "summary": summary,
            "donut_data_json": json.dumps(donut_data),
        },
    )
