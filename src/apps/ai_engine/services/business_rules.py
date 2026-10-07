"""
business_rules.py — Deterministic, explainable business analysis rules.

Phase 6 Step 3: Pure rule evaluation on structured BusinessFeatures vectors.

Principles:
  - 100% deterministic: no machine learning, no guessing, no fabricated estimates.
  - Transparent & explainable: every recommendation carries rule_id,
    triggered_by_value, threshold_value, and plain-English explanation.
  - Safe arithmetic: uses Decimal throughout, guards against division by zero,
    and safely handles None, negative, and zero values.
  - Isolated from ORM: rules operate exclusively on the BusinessFeatures DTO,
    ensuring they can be unit-tested without database access.
  - Domain separation: evaluates enterprise P&L, inventory, and balance-sheet
    metrics distinct from individual property asset rules.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Tuple

from .contracts import (
    AnalysisStatus,
    BusinessFeatures,
    RecommendationCategory,
    RecommendationPriority,
)
from .recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

ZERO = Decimal("0.00")

# ---------------------------------------------------------------------------
# Rule thresholds
# ---------------------------------------------------------------------------
LOW_GROSS_MARGIN_THRESHOLD = Decimal("20.00")         # Gross margin < 20.00% warrants caution
SEVERE_NET_LOSS_MARGIN_THRESHOLD = Decimal("-20.00")  # Net margin <= -20.00% is critical net loss
HIGH_EXPENSE_RATIO_THRESHOLD = Decimal("40.00")       # Operating expenses >= 40.00% of revenue
HIGH_PORTFOLIO_LTV_THRESHOLD = Decimal("80.00")       # Outstanding loans / portfolio value >= 80.00%
HIGH_DEBT_TO_REVENUE_THRESHOLD = Decimal("3.00")      # Outstanding loans >= 3x period revenue
HIGH_PROPERTY_OVERHEAD_THRESHOLD = Decimal("20.00")   # Unallocated property overhead >= 20.00% of revenue
CRITICAL_LOW_STOCK_COUNT_THRESHOLD = 5                # >= 5 products low stock triggers critical depletion
CRITICAL_LOW_STOCK_RATIO_THRESHOLD = Decimal("0.50")  # >= 50% catalog low stock triggers critical depletion


def evaluate_business_rules(
    features: BusinessFeatures,
    engine: RecommendationEngine,
) -> Tuple[AnalysisStatus, List[str], str]:
    """
    Evaluate deterministic business intelligence rules against a BusinessFeatures vector.

    Populates `engine` with prioritised, explainable recommendations.

    Args:
        features: Structured BusinessFeatures DTO extracted by feature_extraction.
        engine:   RecommendationEngine instance for accumulating recommendations.

    Returns:
        (status, insights, summary):
          - status:   AnalysisStatus (OK or INSUFFICIENT_DATA)
          - insights: List of factual bullet points describing detected signals
          - summary:  Human-readable factual executive summary of the business position
    """
    insights: List[str] = []

    # ------------------------------------------------------------------ #
    # 1. Baseline Financial & Operational Completeness Check             #
    # ------------------------------------------------------------------ #
    has_portfolio = features.property_count > 0
    has_products = features.product_count > 0
    has_transactions = (
        features.revenue is not None
        or features.cogs is not None
        or features.operating_expenses is not None
        or features.property_overhead is not None
        or features.total_outstanding_loans is not None
    )

    if not has_portfolio and not has_products and not has_transactions:
        status = AnalysisStatus.INSUFFICIENT_DATA
        insights.append(
            "Business has no recorded properties, products, sales, purchases, or expenses."
        )
        engine.add(
            rule_id="business_missing_operational_baseline",
            title="Record Initial Business Activity",
            description=(
                "No properties, product inventory, or financial transactions are currently "
                "recorded. Add properties, inventory products, or transactions to activate "
                "business health intelligence."
            ),
            priority=RecommendationPriority.MEDIUM,
            category=RecommendationCategory.OPERATIONS,
            triggered_by_value=None,
            threshold_value=None,
            action_url="/analytics/",
        )
        summary = (
            f"Analysis for '{features.business_name}' is limited due to a lack of recorded "
            "operational data. Record properties, products, or financial transactions to "
            "enable business health metrics."
        )
        return status, insights, summary

    # The business has at least one operational facet
    status = AnalysisStatus.OK

    # ------------------------------------------------------------------ #
    # 2. Net Profitability / Loss Analysis                               #
    # ------------------------------------------------------------------ #
    if features.net_profit is not None:
        if features.net_profit < ZERO:
            if (
                features.net_margin_pct is not None
                and features.net_margin_pct <= SEVERE_NET_LOSS_MARGIN_THRESHOLD
            ):
                engine.add(
                    rule_id="business_severe_net_loss",
                    title="Severe Operating Net Loss",
                    description=(
                        f"Business incurred a severe net loss of ₹{abs(features.net_profit)} "
                        f"({features.net_margin_pct}% net margin). Operating costs and COGS "
                        "substantially exceed revenue."
                    ),
                    priority=RecommendationPriority.CRITICAL,
                    category=RecommendationCategory.FINANCE,
                    triggered_by_value=features.net_margin_pct,
                    threshold_value=SEVERE_NET_LOSS_MARGIN_THRESHOLD,
                    action_url="/analytics/",
                )
                insights.append(
                    f"Operating at a severe net loss of ₹{abs(features.net_profit)} "
                    f"({features.net_margin_pct}% net margin)."
                )
            else:
                engine.add(
                    rule_id="business_net_loss",
                    title="Operating Net Loss",
                    description=(
                        f"Business incurred an overall net loss of ₹{abs(features.net_profit)}. "
                        "Review operating expenses and cost structure to return to profitability."
                    ),
                    priority=RecommendationPriority.HIGH,
                    category=RecommendationCategory.FINANCE,
                    triggered_by_value=features.net_profit,
                    threshold_value=ZERO,
                    action_url="/analytics/",
                )
                insights.append(
                    f"Operating at a net loss of ₹{abs(features.net_profit)}."
                )
        elif features.net_profit > ZERO:
            margin_str = f" ({features.net_margin_pct}% net margin)" if features.net_margin_pct is not None else ""
            insights.append(
                f"Profitable operating performance: net profit of ₹{features.net_profit}{margin_str}."
            )

    # ------------------------------------------------------------------ #
    # 3. Gross Margin Health (COGS vs Revenue)                           #
    # ------------------------------------------------------------------ #
    if features.revenue is not None and features.revenue > ZERO:
        if features.gross_margin_pct is not None:
            if features.gross_margin_pct < ZERO:
                engine.add(
                    rule_id="business_negative_gross_margin",
                    title="Negative Gross Profit Margin",
                    description=(
                        f"Cost of goods sold (₹{features.cogs or ZERO}) exceeds sales revenue "
                        f"(₹{features.revenue}), resulting in negative gross margin "
                        f"({features.gross_margin_pct}%). Review product pricing or supplier costs immediately."
                    ),
                    priority=RecommendationPriority.CRITICAL,
                    category=RecommendationCategory.FINANCE,
                    triggered_by_value=features.gross_margin_pct,
                    threshold_value=ZERO,
                    action_url="/transactions/purchases/",
                )
                insights.append(
                    f"Direct procurement costs exceed sales revenue: gross margin is {features.gross_margin_pct}%."
                )
            elif features.gross_margin_pct < LOW_GROSS_MARGIN_THRESHOLD:
                engine.add(
                    rule_id="business_low_gross_margin",
                    title="Low Gross Profit Margin",
                    description=(
                        f"Gross profit margin of {features.gross_margin_pct}% is below the prudent "
                        f"{LOW_GROSS_MARGIN_THRESHOLD}% benchmark (Revenue: ₹{features.revenue}, "
                        f"COGS: ₹{features.cogs or ZERO}). Margins may be insufficient to cover operating overhead."
                    ),
                    priority=RecommendationPriority.HIGH,
                    category=RecommendationCategory.FINANCE,
                    triggered_by_value=features.gross_margin_pct,
                    threshold_value=LOW_GROSS_MARGIN_THRESHOLD,
                    action_url="/transactions/purchases/",
                )
                insights.append(
                    f"Gross margin of {features.gross_margin_pct}% is below {LOW_GROSS_MARGIN_THRESHOLD}% benchmark."
                )
            else:
                insights.append(
                    f"Healthy gross profit margin of {features.gross_margin_pct}%."
                )

    # ------------------------------------------------------------------ #
    # 4. Operating Expense Burden                                        #
    # ------------------------------------------------------------------ #
    if (
        features.revenue is not None
        and features.revenue > ZERO
        and features.expense_ratio_pct is not None
    ):
        if features.expense_ratio_pct >= HIGH_EXPENSE_RATIO_THRESHOLD:
            engine.add(
                rule_id="business_high_expense_burden",
                title="High Operating Expense Burden",
                description=(
                    f"Operating expenses of ₹{features.operating_expenses} consume "
                    f"{features.expense_ratio_pct}% of total revenue (₹{features.revenue}), "
                    f"exceeding the {HIGH_EXPENSE_RATIO_THRESHOLD}% benchmark. "
                    "Review overhead, administrative, and utility expenses."
                ),
                priority=RecommendationPriority.MEDIUM,
                category=RecommendationCategory.FINANCE,
                triggered_by_value=features.expense_ratio_pct,
                threshold_value=HIGH_EXPENSE_RATIO_THRESHOLD,
                action_url="/transactions/expenses/",
            )
            insights.append(
                f"Operating expenses consume {features.expense_ratio_pct}% of revenue."
            )

    # ------------------------------------------------------------------ #
    # 5. Unallocated Property Overhead Drag                              #
    # ------------------------------------------------------------------ #
    if (
        features.revenue is not None
        and features.revenue > ZERO
        and features.property_overhead is not None
        and features.property_overhead > ZERO
    ):
        overhead_ratio = (
            features.property_overhead / features.revenue * 100
        ).quantize(Decimal("0.01"))
        if overhead_ratio >= HIGH_PROPERTY_OVERHEAD_THRESHOLD:
            engine.add(
                rule_id="business_high_property_overhead",
                title="High General Property Overhead",
                description=(
                    f"Unallocated property overhead of ₹{features.property_overhead} accounts for "
                    f"{overhead_ratio}% of total revenue. Audit unassigned maintenance and shared property expenses."
                ),
                priority=RecommendationPriority.MEDIUM,
                category=RecommendationCategory.FINANCE,
                triggered_by_value=overhead_ratio,
                threshold_value=HIGH_PROPERTY_OVERHEAD_THRESHOLD,
                action_url="/finances/categories/",
            )
            insights.append(
                f"Unallocated property overhead equals {overhead_ratio}% of revenue."
            )

    # ------------------------------------------------------------------ #
    # 6. Inventory & Stock Depletion Health                              #
    # ------------------------------------------------------------------ #
    if features.low_stock_product_count > 0:
        is_critical = (
            features.low_stock_product_count >= CRITICAL_LOW_STOCK_COUNT_THRESHOLD
            or (
                features.product_count > 0
                and (
                    Decimal(str(features.low_stock_product_count))
                    / Decimal(str(features.product_count))
                )
                >= CRITICAL_LOW_STOCK_RATIO_THRESHOLD
            )
        )
        if is_critical:
            engine.add(
                rule_id="business_critical_stock_depletion",
                title="Critical Inventory Stock Depletion",
                description=(
                    f"{features.low_stock_product_count} of {features.product_count} active product(s) "
                    "are at or below reorder levels. Restock inventory urgently to avoid stock-outs and unfulfilled orders."
                ),
                priority=RecommendationPriority.HIGH,
                category=RecommendationCategory.INVENTORY,
                triggered_by_value=Decimal(str(features.low_stock_product_count)),
                threshold_value=Decimal("1"),
                action_url="/inventory/stock/",
            )
            insights.append(
                f"Critical inventory risk: {features.low_stock_product_count} of {features.product_count} product(s) at or below reorder level."
            )
        else:
            engine.add(
                rule_id="business_low_stock_risk",
                title="Low Inventory Stock Alert",
                description=(
                    f"{features.low_stock_product_count} active product(s) have reached or fallen below "
                    "reorder thresholds. Review stock levels and issue purchase orders."
                ),
                priority=RecommendationPriority.MEDIUM,
                category=RecommendationCategory.INVENTORY,
                triggered_by_value=Decimal(str(features.low_stock_product_count)),
                threshold_value=Decimal("1"),
                action_url="/inventory/stock/",
            )
            insights.append(
                f"{features.low_stock_product_count} active product(s) at or below reorder level."
            )

    # ------------------------------------------------------------------ #
    # 7. Missing Sales Activity with Active Products                     #
    # ------------------------------------------------------------------ #
    if features.product_count > 0 and (features.revenue is None or features.revenue == ZERO):
        engine.add(
            rule_id="business_no_sales_recorded",
            title="Record First Sales Transactions",
            description=(
                f"The business has {features.product_count} active product(s) listed in catalog, "
                "but ₹0.00 in revenue recorded. Record sales transactions to track customer demand and margins."
            ),
            priority=RecommendationPriority.LOW,
            category=RecommendationCategory.GROWTH,
            triggered_by_value=None,
            threshold_value=None,
            action_url="/transactions/sales/add/",
        )
        insights.append(
            f"Catalog contains {features.product_count} product(s) with zero sales transactions recorded."
        )

    # ------------------------------------------------------------------ #
    # 8. Portfolio Debt Leverage (LTV)                                   #
    # ------------------------------------------------------------------ #
    if (
        features.total_outstanding_loans is not None
        and features.total_outstanding_loans > ZERO
        and features.total_portfolio_value is not None
        and features.total_portfolio_value > ZERO
    ):
        portfolio_ltv = (
            features.total_outstanding_loans / features.total_portfolio_value * 100
        ).quantize(Decimal("0.01"))
        if portfolio_ltv >= HIGH_PORTFOLIO_LTV_THRESHOLD:
            engine.add(
                rule_id="business_high_portfolio_leverage",
                title="High Portfolio Debt Leverage",
                description=(
                    f"Total outstanding property loans of ₹{features.total_outstanding_loans} represent "
                    f"{portfolio_ltv}% of total portfolio value (₹{features.total_portfolio_value}), "
                    f"exceeding the {HIGH_PORTFOLIO_LTV_THRESHOLD}% leverage threshold."
                ),
                priority=RecommendationPriority.HIGH,
                category=RecommendationCategory.FINANCE,
                triggered_by_value=portfolio_ltv,
                threshold_value=HIGH_PORTFOLIO_LTV_THRESHOLD,
                action_url="/analytics/portfolio/",
            )
            insights.append(
                f"Portfolio leverage is high: outstanding debt is {portfolio_ltv}% of portfolio value."
            )

    # ------------------------------------------------------------------ #
    # 9. High Debt-to-Revenue Exposure                                   #
    # ------------------------------------------------------------------ #
    if (
        features.total_outstanding_loans is not None
        and features.total_outstanding_loans > ZERO
        and features.revenue is not None
        and features.revenue > ZERO
    ):
        debt_to_revenue = (
            features.total_outstanding_loans / features.revenue
        ).quantize(Decimal("0.01"))
        if debt_to_revenue >= HIGH_DEBT_TO_REVENUE_THRESHOLD:
            engine.add(
                rule_id="business_high_debt_to_revenue",
                title="High Debt-to-Revenue Exposure",
                description=(
                    f"Total outstanding debt of ₹{features.total_outstanding_loans} is "
                    f"{debt_to_revenue}x total revenue (₹{features.revenue}), exceeding the "
                    f"{HIGH_DEBT_TO_REVENUE_THRESHOLD}x threshold. Monitor debt service capacity against operating cash flows."
                ),
                priority=RecommendationPriority.MEDIUM,
                category=RecommendationCategory.FINANCE,
                triggered_by_value=debt_to_revenue,
                threshold_value=HIGH_DEBT_TO_REVENUE_THRESHOLD,
                action_url="/analytics/",
            )
            insights.append(
                f"Outstanding debt is {debt_to_revenue}x total revenue."
            )

    # ------------------------------------------------------------------ #
    # 10. Structured Factual Summary Generation                          #
    # ------------------------------------------------------------------ #
    if features.revenue is not None and features.net_profit is not None:
        pnl_str = f"+₹{features.net_profit}" if features.net_profit >= ZERO else f"-₹{abs(features.net_profit)}"
        net_margin_str = f"{features.net_margin_pct}%" if features.net_margin_pct is not None else "N/A"
        headline = (
            f"{features.business_name}: Revenue ₹{features.revenue}, Net Profit {pnl_str} "
            f"({net_margin_str} net margin), {features.property_count} properties, {features.product_count} active products."
        )
    elif features.property_count > 0:
        val_str = f"₹{features.total_portfolio_value}" if features.total_portfolio_value is not None else "unrecorded"
        headline = (
            f"{features.business_name}: Portfolio of {features.property_count} property assets "
            f"(total value: {val_str}). No commercial sales or purchase transactions recorded."
        )
    elif features.product_count > 0:
        headline = (
            f"{features.business_name}: Catalog of {features.product_count} active products. "
            "No sales transactions recorded."
        )
    else:
        headline = f"{features.business_name}: Operational baseline pending."

    finding_count = engine.count()
    if finding_count > 0:
        headline += f" Identified {finding_count} actionable finding(s)."
    else:
        headline += " No critical risk flags or urgent actions identified."

    summary = headline
    return status, insights, summary
