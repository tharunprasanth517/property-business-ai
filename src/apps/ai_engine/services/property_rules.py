"""
property_rules.py — Deterministic, explainable property analysis rules.

Phase 6 Step 2: Pure rule evaluation on structured PropertyFeatures vectors.

Principles:
  - 100% deterministic: no machine learning, no guessing, no fabricated estimates.
  - Transparent & explainable: every recommendation carries rule_id,
    triggered_by_value, threshold_value, and plain-English explanation.
  - Safe arithmetic: uses Decimal throughout, guards against division by zero,
    and safely handles None, negative, and zero values.
  - Isolated from ORM: rules operate exclusively on the PropertyFeatures DTO,
    ensuring they can be unit-tested without database access.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Tuple

from .contracts import (
    AnalysisStatus,
    PropertyFeatures,
    RecommendationCategory,
    RecommendationPriority,
)
from .recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

ZERO = Decimal("0.00")

# ---------------------------------------------------------------------------
# Rule thresholds
# ---------------------------------------------------------------------------
HIGH_LTV_THRESHOLD = Decimal("80.00")           # LTV >= 80% warrants caution
CRITICAL_LTV_THRESHOLD = Decimal("100.00")       # LTV > 100% is underwater
NEGATIVE_ROI_SEVERE_THRESHOLD = Decimal("-15.00") # ROI <= -15% is high urgency
HIGH_EXPENSE_RATIO_THRESHOLD = Decimal("25.00")  # Expenses >= 25% of purchase cost
EXTENDED_HOLDING_DAYS_THRESHOLD = 365            # 1+ year held in RAW / ON_HOLD


def evaluate_property_rules(
    features: PropertyFeatures,
    engine: RecommendationEngine,
) -> Tuple[AnalysisStatus, List[str], str]:
    """
    Evaluate deterministic property intelligence rules against a PropertyFeatures vector.

    Populates `engine` with prioritised, explainable recommendations.

    Args:
        features: Structured PropertyFeatures DTO extracted by feature_extraction.
        engine:   RecommendationEngine instance for accumulating recommendations.

    Returns:
        (status, insights, summary):
          - status:   AnalysisStatus (OK or INSUFFICIENT_DATA)
          - insights: List of factual bullet points describing detected signals
          - summary:  Human-readable factual summary of the property position
    """
    insights: List[str] = []

    # ------------------------------------------------------------------ #
    # 1. Baseline Financial Completeness Check                            #
    # ------------------------------------------------------------------ #
    if features.purchase_price is None and features.current_estimated_value is None:
        status = AnalysisStatus.INSUFFICIENT_DATA
        insights.append(
            "Property lacks both purchase price and current estimated value records."
        )
        engine.add(
            rule_id="property_missing_financial_baseline",
            title="Record Property Financial Baseline",
            description=(
                "Neither purchase price nor current estimated value is recorded. "
                "Add purchase price and current valuation to enable financial intelligence "
                "and return metrics."
            ),
            priority=RecommendationPriority.MEDIUM,
            category=RecommendationCategory.PROPERTY,
            triggered_by_value=None,
            threshold_value=None,
            action_url=f"/businesses/properties/{features.property_id}/edit/",
        )
        summary = (
            f"Analysis for '{features.property_name}' ({features.property_type}) "
            "is limited due to missing financial baseline data (purchase price and "
            "current estimated value). Recording these figures is required for return "
            "and leverage metrics."
        )
        return status, insights, summary

    # Property has at least partial baseline
    status = AnalysisStatus.OK

    if features.purchase_price is None and features.current_estimated_value is not None:
        insights.append(
            "Original purchase price is unrecorded; invested capital and ROI cannot be calculated."
        )
        engine.add(
            rule_id="property_missing_purchase_price",
            title="Record Original Purchase Price",
            description=(
                "Record the acquisition purchase price to track total invested capital "
                "and overall return on investment."
            ),
            priority=RecommendationPriority.LOW,
            category=RecommendationCategory.PROPERTY,
            triggered_by_value=None,
            threshold_value=None,
            action_url=f"/businesses/properties/{features.property_id}/edit/",
        )

    if features.purchase_price is not None and features.current_estimated_value is None:
        insights.append(
            "Current estimated market value is missing; unrealised P&L and loan-to-value cannot be calculated."
        )
        engine.add(
            rule_id="property_missing_valuation",
            title="Update Current Estimated Value",
            description=(
                "Recording an updated market value estimate enables real-time P&L, "
                "return on investment, and leverage analysis."
            ),
            priority=RecommendationPriority.LOW,
            category=RecommendationCategory.PROPERTY,
            triggered_by_value=None,
            threshold_value=None,
            action_url=f"/businesses/properties/{features.property_id}/edit/",
        )

    # ------------------------------------------------------------------ #
    # 2. Leverage / Loan-to-Value (LTV) Risk                              #
    # ------------------------------------------------------------------ #
    if features.loan_to_value_ratio is not None:
        if features.loan_to_value_ratio > CRITICAL_LTV_THRESHOLD:
            engine.add(
                rule_id="property_ltv_underwater",
                title="Property Loan Underwater (LTV > 100%)",
                description=(
                    f"Outstanding loan balance (₹{features.outstanding_loan_balance}) "
                    f"exceeds current estimated property value (₹{features.current_estimated_value}). "
                    f"Loan-to-value ratio is {features.loan_to_value_ratio}%, "
                    "indicating negative equity leverage."
                ),
                priority=RecommendationPriority.CRITICAL,
                category=RecommendationCategory.FINANCE,
                triggered_by_value=features.loan_to_value_ratio,
                threshold_value=CRITICAL_LTV_THRESHOLD,
                action_url=f"/finances/properties/{features.property_id}/loans/",
            )
            insights.append(
                f"Outstanding debt exceeds property value (LTV: {features.loan_to_value_ratio}%)."
            )
        elif features.loan_to_value_ratio >= HIGH_LTV_THRESHOLD:
            engine.add(
                rule_id="property_high_ltv",
                title="High Loan-to-Value Exposure",
                description=(
                    f"Outstanding debt of ₹{features.outstanding_loan_balance} represents "
                    f"{features.loan_to_value_ratio}% of current estimated property value "
                    f"(₹{features.current_estimated_value}), exceeding the "
                    f"{HIGH_LTV_THRESHOLD}% prudent leverage threshold."
                ),
                priority=RecommendationPriority.HIGH,
                category=RecommendationCategory.FINANCE,
                triggered_by_value=features.loan_to_value_ratio,
                threshold_value=HIGH_LTV_THRESHOLD,
                action_url=f"/finances/properties/{features.property_id}/loans/",
            )
            insights.append(
                f"High leverage exposure with LTV at {features.loan_to_value_ratio}%."
            )

    # ------------------------------------------------------------------ #
    # 3. Negative Return on Investment (Unrealised Loss)                  #
    # ------------------------------------------------------------------ #
    if features.current_roi_pct is not None and features.current_roi_pct < Decimal("0.00"):
        current_pnl = (features.current_estimated_value or ZERO) - (
            features.total_invested or ZERO
        )
        if features.current_roi_pct <= NEGATIVE_ROI_SEVERE_THRESHOLD:
            engine.add(
                rule_id="property_severe_negative_roi",
                title="Severe Unrealised Capital Loss",
                description=(
                    f"The property has an unrealised capital loss of ₹{abs(current_pnl)} "
                    f"({features.current_roi_pct}% ROI). Total invested capital "
                    f"(₹{features.total_invested}) significantly exceeds current estimated value "
                    f"(₹{features.current_estimated_value})."
                ),
                priority=RecommendationPriority.HIGH,
                category=RecommendationCategory.PROPERTY,
                triggered_by_value=features.current_roi_pct,
                threshold_value=Decimal("0.00"),
                action_url=f"/businesses/properties/{features.property_id}/",
            )
        else:
            engine.add(
                rule_id="property_negative_roi",
                title="Unrealised Capital Loss",
                description=(
                    f"Current estimated value (₹{features.current_estimated_value}) is below "
                    f"total invested capital (₹{features.total_invested}), yielding an "
                    f"unrealised loss of ₹{abs(current_pnl)} ({features.current_roi_pct}% ROI)."
                ),
                priority=RecommendationPriority.MEDIUM,
                category=RecommendationCategory.PROPERTY,
                triggered_by_value=features.current_roi_pct,
                threshold_value=Decimal("0.00"),
                action_url=f"/businesses/properties/{features.property_id}/",
            )
        insights.append(
            f"Property operates at an unrealised loss of ₹{abs(current_pnl)} "
            f"({features.current_roi_pct}% ROI)."
        )

    # ------------------------------------------------------------------ #
    # 4. High Expense Overhead / Cost Drag                                #
    # ------------------------------------------------------------------ #
    if (
        features.purchase_price is not None
        and features.purchase_price > ZERO
        and features.total_expenses is not None
        and features.total_expenses > ZERO
    ):
        expense_ratio = (
            features.total_expenses / features.purchase_price * 100
        ).quantize(Decimal("0.01"))
        if expense_ratio >= HIGH_EXPENSE_RATIO_THRESHOLD:
            engine.add(
                rule_id="property_high_expense_overhead",
                title="High Operating Expense Overhead",
                description=(
                    f"Cumulative expenses of ₹{features.total_expenses} represent "
                    f"{expense_ratio}% of original purchase price (₹{features.purchase_price}). "
                    "Review operating expenses to prevent further cost drag."
                ),
                priority=RecommendationPriority.MEDIUM,
                category=RecommendationCategory.FINANCE,
                triggered_by_value=expense_ratio,
                threshold_value=HIGH_EXPENSE_RATIO_THRESHOLD,
                action_url=f"/finances/properties/{features.property_id}/expenses/",
            )
            insights.append(
                f"Cumulative expenses equal {expense_ratio}% of acquisition cost."
            )

    # ------------------------------------------------------------------ #
    # 5. Target Selling Price Achieved                                    #
    # ------------------------------------------------------------------ #
    if (
        features.current_estimated_value is not None
        and features.expected_selling_price is not None
        and features.expected_selling_price > ZERO
    ):
        if features.current_estimated_value >= features.expected_selling_price:
            engine.add(
                rule_id="property_selling_target_met",
                title="Selling Target Price Achieved",
                description=(
                    f"Current estimated value (₹{features.current_estimated_value}) has reached "
                    f"or surpassed the expected selling price target of ₹{features.expected_selling_price}. "
                    "Evaluate market conditions for potential exit or target revision."
                ),
                priority=RecommendationPriority.LOW,
                category=RecommendationCategory.GROWTH,
                triggered_by_value=features.current_estimated_value,
                threshold_value=features.expected_selling_price,
                action_url=f"/finances/properties/{features.property_id}/transactions/",
            )
            insights.append(
                f"Current estimated value meets or exceeds the target selling price of ₹{features.expected_selling_price}."
            )

    # ------------------------------------------------------------------ #
    # 6. Stalled Development / Extended Raw Holding Period                #
    # ------------------------------------------------------------------ #
    if (
        features.development_status in ("RAW", "ON_HOLD")
        and features.days_held is not None
        and features.days_held >= EXTENDED_HOLDING_DAYS_THRESHOLD
    ):
        holding_costs = (features.total_expenses or ZERO) + (
            features.total_interest_paid or ZERO
        )
        engine.add(
            rule_id="property_stalled_development",
            title="Extended Undeveloped Holding Period",
            description=(
                f"Property has been held for {features.days_held} days with status "
                f"'{features.development_status}'. Cumulative holding expenses and debt interest "
                f"total ₹{holding_costs}. Consider moving forward with development or "
                "reviewing asset strategy."
            ),
            priority=RecommendationPriority.LOW,
            category=RecommendationCategory.OPERATIONS,
            triggered_by_value=Decimal(str(features.days_held)),
            threshold_value=Decimal(str(EXTENDED_HOLDING_DAYS_THRESHOLD)),
            action_url=f"/businesses/properties/{features.property_id}/edit/",
        )
        insights.append(
            f"Property held undeveloped for {features.days_held} days in '{features.development_status}' status."
        )

    # ------------------------------------------------------------------ #
    # 7. Structured Factual Summary Generation                            #
    # ------------------------------------------------------------------ #
    if features.total_invested is not None and features.current_estimated_value is not None:
        pnl = features.current_estimated_value - features.total_invested
        pnl_str = f"+₹{pnl}" if pnl >= 0 else f"-₹{abs(pnl)}"
        roi_str = (
            f"{features.current_roi_pct}%"
            if features.current_roi_pct is not None
            else "N/A"
        )
        headline = (
            f"{features.property_name} ({features.property_type}, {features.ownership_status}): "
            f"Total invested capital is ₹{features.total_invested} with current estimated value "
            f"of ₹{features.current_estimated_value} (unrealised P&L: {pnl_str}, ROI: {roi_str})."
        )
    elif features.current_estimated_value is not None:
        headline = (
            f"{features.property_name} ({features.property_type}, {features.ownership_status}): "
            f"Current estimated value is ₹{features.current_estimated_value}. "
            "Original purchase price is unrecorded."
        )
    else:
        headline = (
            f"{features.property_name} ({features.property_type}, {features.ownership_status}): "
            f"Purchase price is ₹{features.purchase_price}. "
            "Current market valuation is unrecorded."
        )

    finding_count = engine.count()
    if finding_count > 0:
        headline += f" Identified {finding_count} actionable finding(s)."
    else:
        headline += " No critical risk flags or urgent actions identified."

    summary = headline
    return status, insights, summary
