"""
property_analysis.py — Property-level intelligence service boundary.

Phase 6 Step 2: Integrates deterministic, explainable property analysis rules.

The public function ``analyse_property`` is the single entry point for
consuming code (views, management commands, background tasks). It:

  1. Retrieves a tenant-verified PropertyContext via context.py.
  2. Extracts a PropertyFeatures vector via feature_extraction.py.
  3. Evaluates deterministic property intelligence rules via property_rules.py.
  4. Returns a typed PropertyAnalysisResult with status, insights,
     prioritised recommendations, and explainable summary.

Design note: ``analyse_property`` accepts a raw user and property_id so that
callers do not need to manage context objects themselves. The tenant check
happens inside ``get_property_context`` which raises Http404 or PermissionDenied
on any access violation — callers do not need additional guards.
"""

from __future__ import annotations

import logging

from .contracts import AnalysisStatus, PropertyAnalysisResult
from .context import get_property_context
from .feature_extraction import extract_property_features
from .property_rules import evaluate_property_rules
from .recommendation_engine import RecommendationEngine


logger = logging.getLogger(__name__)


def analyse_property(user, property_id: int) -> PropertyAnalysisResult:
    """
    Run the property intelligence pipeline for a single property.

    Args:
        user:        Authenticated Django User (request.user or equivalent).
        property_id: Primary key of the Property to analyse.

    Returns:
        PropertyAnalysisResult with:
          - status = AnalysisStatus.OK or INSUFFICIENT_DATA
          - features = PropertyFeatures populated from ORM data
          - insights = List of factual observation strings
          - recommendations = List of prioritised, explainable Recommendation objects
          - summary = Factual executive summary
          - investment_score = None (ML/heuristic score reserved for future step)

    Raises:
        django.core.exceptions.PermissionDenied
            If user is not authenticated or has no accessible businesses.
        django.http.Http404
            If property_id does not exist within the user's accessible businesses.

    Note: This function does NOT catch Http404 or PermissionDenied — they
          propagate naturally to the view/middleware layer.
    """
    # Step 1: Tenant-safe context (raises Http404 or PermissionDenied on violation)
    ctx = get_property_context(user, property_id)

    # Step 2: Feature extraction (pure data mapping, no intelligence)
    features = extract_property_features(ctx)

    # Step 3: Rule evaluation & recommendation engine accumulation
    engine = RecommendationEngine(business_id=ctx.business_id)
    status, insights, summary = evaluate_property_rules(features, engine)

    recommendations = engine.get_sorted()

    logger.debug(
        "analyse_property: property_id=%d business_id=%d status=%s recommendations=%d",
        property_id,
        ctx.business_id,
        status.value,
        len(recommendations),
    )

    return PropertyAnalysisResult(
        property_id=ctx.property_id,
        business_id=ctx.business_id,
        status=status,
        features=features,
        investment_score=None,
        insights=insights,
        recommendations=recommendations,
        summary=summary,
    )

