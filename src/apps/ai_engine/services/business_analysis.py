"""
business_analysis.py — Business-level intelligence service boundary.

Phase 6 Step 3: Integrates deterministic, explainable business analysis rules.

The public function ``analyse_business`` is the single entry point for
consuming code.  It:

  1. Retrieves a tenant-verified BusinessContext via context.py.
  2. Extracts a BusinessFeatures vector via feature_extraction.py.
  3. Evaluates deterministic business intelligence rules via business_rules.py.
  4. Returns a typed BusinessAnalysisResult with status, insights,
     prioritised recommendations, and explainable executive summary.

Raises Http404 or PermissionDenied on any tenant violation — same contract
as property_analysis.analyse_property.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from .contracts import AnalysisStatus, BusinessAnalysisResult
from .context import get_business_context
from .feature_extraction import extract_business_features
from .business_rules import evaluate_business_rules
from .recommendation_engine import RecommendationEngine


logger = logging.getLogger(__name__)


def analyse_business(
    user,
    business_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> BusinessAnalysisResult:
    """
    Run the business intelligence pipeline for a single business.

    Args:
        user:        Authenticated Django User.
        business_id: PK of the Business to analyse.  If None, the first
                     accessible business for the user is used (mirrors the
                     platform's active-business convention).
        date_from:   Optional start of the P&L date window (inclusive).
        date_to:     Optional end of the P&L date window (inclusive).

    Returns:
        BusinessAnalysisResult with:
          - status = AnalysisStatus.OK or INSUFFICIENT_DATA
          - features = BusinessFeatures populated from ORM data
          - insights = List of factual observation strings
          - recommendations = List of prioritised, explainable Recommendation objects
          - summary = Factual executive summary
          - health_score = None (ML/heuristic score reserved for future step)
          - score_breakdown = {} (reserved for future step)

    Raises:
        django.core.exceptions.PermissionDenied
            If user is not authenticated or has no accessible businesses.
        django.http.Http404
            If business_id is provided but not accessible by the user.
    """
    # Step 1: Tenant-safe context (raises Http404 or PermissionDenied on violation)
    ctx = get_business_context(user, business_id)

    # Step 2: Feature extraction (pure data mapping, no intelligence)
    features = extract_business_features(ctx, date_from=date_from, date_to=date_to)

    # Step 3: Rule evaluation & recommendation engine accumulation
    engine = RecommendationEngine(business_id=ctx.business_id)
    status, insights, summary = evaluate_business_rules(features, engine)

    recommendations = engine.get_sorted()

    logger.debug(
        "analyse_business: business_id=%d status=%s recommendations=%d",
        ctx.business_id,
        status.value,
        len(recommendations),
    )

    return BusinessAnalysisResult(
        business_id=ctx.business_id,
        status=status,
        features=features,
        health_score=None,
        score_breakdown={},
        insights=insights,
        recommendations=recommendations,
        summary=summary,
    )
