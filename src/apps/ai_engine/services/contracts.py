"""
contracts.py — Typed service boundaries for the ai_engine intelligence layer.

All data-transfer objects (DTOs) used across ai_engine services are defined
here.  They are plain Python dataclasses so they can be instantiated, compared,
and serialised without touching the ORM.

Design principles:
  - Decimal is used for ALL monetary / ratio values.  Never coerce to float
    at the boundary; callers that need floats (e.g. Chart.js) convert locally.
  - Optional[X] = None signals "not yet computed" or "data unavailable".
  - Every DTO carries a ``business_id`` so the calling layer can assert tenant
    isolation before acting on the result.

No Django imports are present in this file — contracts must remain importable
in any Python context (unit tests, management commands, Celery tasks).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AnalysisStatus(str, Enum):
    """Lifecycle status of a completed analysis result."""

    OK = "ok"                    # Analysis ran successfully.
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough records to analyse.
    ERROR = "error"              # An unexpected error occurred.


class RecommendationPriority(str, Enum):
    """Urgency level attached to a single recommendation."""

    CRITICAL = "critical"   # Immediate action required.
    HIGH = "high"           # Action required this week.
    MEDIUM = "medium"       # Action required this month.
    LOW = "low"             # Informational / nice-to-have.


class RecommendationCategory(str, Enum):
    """Domain bucket for a recommendation — used for UI grouping / filtering."""

    PROPERTY = "property"
    INVENTORY = "inventory"
    FINANCE = "finance"
    OPERATIONS = "operations"
    GROWTH = "growth"


# ---------------------------------------------------------------------------
# Feature vectors (input to analysis services)
# ---------------------------------------------------------------------------


@dataclass
class PropertyFeatures:
    """
    Structured feature set extracted from a single Property record and its
    related financial data.

    All monetary fields use Decimal.  Ratios (e.g. roi_pct) are Decimal too.
    None means the value could not be computed (e.g. missing purchase price).
    """

    # Identity — always present
    property_id: int
    business_id: int
    property_name: str
    property_type: str            # e.g. "LAND", "COMMERCIAL"
    ownership_status: str         # e.g. "OWNED", "LEASED"
    development_status: str       # e.g. "RAW", "DEVELOPED"

    # Geometry
    area: Optional[Decimal] = None
    area_unit: str = "sq ft"

    # Financial — may be None if not recorded
    purchase_price: Optional[Decimal] = None
    current_estimated_value: Optional[Decimal] = None
    expected_selling_price: Optional[Decimal] = None
    total_expenses: Optional[Decimal] = None
    total_loan_principal: Optional[Decimal] = None
    outstanding_loan_balance: Optional[Decimal] = None
    total_interest_paid: Optional[Decimal] = None
    total_invested: Optional[Decimal] = None  # purchase + expenses + interest

    # Computed ratios — None if inputs are unavailable or zero
    current_roi_pct: Optional[Decimal] = None
    potential_roi_pct: Optional[Decimal] = None
    loan_to_value_ratio: Optional[Decimal] = None  # outstanding / estimated_value

    # Temporal
    purchase_date: Optional[date] = None
    days_held: Optional[int] = None   # calendar days since purchase_date

    # Counts
    expense_count: int = 0
    loan_count: int = 0
    active_loan_count: int = 0

    # Extensible metadata (arbitrary key→value pairs for future signals)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessFeatures:
    """
    Structured feature set extracted from a Business and its operational data
    across the full history (or an optional date range).
    """

    # Identity — always present
    business_id: int
    business_name: str

    # P&L aggregates (Decimal — None if no transactions exist)
    revenue: Optional[Decimal] = None
    cogs: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    operating_expenses: Optional[Decimal] = None
    property_overhead: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None

    # Ratios (None if denominators are zero / unavailable)
    gross_margin_pct: Optional[Decimal] = None   # gross_profit / revenue * 100
    net_margin_pct: Optional[Decimal] = None     # net_profit / revenue * 100
    expense_ratio_pct: Optional[Decimal] = None  # opex / revenue * 100

    # Portfolio
    property_count: int = 0
    total_portfolio_value: Optional[Decimal] = None
    total_outstanding_loans: Optional[Decimal] = None

    # Inventory / product
    product_count: int = 0
    low_stock_product_count: int = 0
    total_stock_value: Optional[Decimal] = None  # sum(qty * cost_price)

    # Temporal
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    transaction_days: int = 0  # number of distinct days with any transaction

    # Extensible metadata
    extra: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Analysis results (output from analysis services)
# ---------------------------------------------------------------------------


@dataclass
class PropertyAnalysisResult:
    """
    Output of the property intelligence layer for a single property.

    In Phase 6 Step 1 this carries only the extracted features and a status.
    Rule-based signals and scores will be populated in Step 2.
    """

    property_id: int
    business_id: int
    status: AnalysisStatus
    features: Optional[PropertyFeatures] = None

    # Computed scores (0–100, None until scoring is implemented)
    investment_score: Optional[int] = None

    # Ordered list of insights/flags (populated in Step 2+)
    insights: List[str] = field(default_factory=list)

    # Ordered list of recommended actions (populated in Step 2+)
    recommendations: List["Recommendation"] = field(default_factory=list)

    # Human-readable summary (populated in Step 2+)
    summary: str = ""

    # Error / diagnostic detail (set when status == ERROR)
    error_detail: str = ""


@dataclass
class BusinessAnalysisResult:
    """
    Output of the business intelligence layer for a single business.

    In Phase 6 Step 1 this carries only the extracted features and a status.
    The Business Health Score and action plan will be added in Step 2.
    """

    business_id: int
    status: AnalysisStatus
    features: Optional[BusinessFeatures] = None

    # Business Health Score (0–100), None until scoring is implemented
    health_score: Optional[int] = None

    # Score breakdown by dimension (populated in Step 2+)
    score_breakdown: Dict[str, int] = field(default_factory=dict)

    # Ordered list of factual insights/observations (populated in Step 3+)
    insights: List[str] = field(default_factory=list)

    # Ordered list of recommended actions (populated in Step 2+)
    recommendations: List["Recommendation"] = field(default_factory=list)

    # Human-readable executive summary (populated in Step 2+)
    summary: str = ""

    # Error / diagnostic detail (set when status == ERROR)
    error_detail: str = ""


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


@dataclass
class Recommendation:
    """
    A single actionable insight returned by the recommendation engine.

    Designed to be explainable: every recommendation carries the rule or
    signal that triggered it so the UI can show "why" alongside "what".

    Priority and category are used for sorting / filtering in the UI.
    """

    title: str                         # Short one-line label (e.g. "Reorder stock")
    description: str                   # Expanded explanation for the user
    priority: RecommendationPriority
    category: RecommendationCategory

    # Machine-readable rule identifier — stable across runs (e.g. "low_stock_alert")
    rule_id: str = ""

    # The computed signal value that triggered this rule (for UI display)
    triggered_by_value: Optional[Decimal] = None

    # The threshold that was breached (for UI display)
    threshold_value: Optional[Decimal] = None

    # Deep-link into the application that the user should act on
    action_url: str = ""

    # Extensible metadata (e.g. {"product_id": 42, "product_name": "Cement"})
    metadata: Dict[str, Any] = field(default_factory=dict)
