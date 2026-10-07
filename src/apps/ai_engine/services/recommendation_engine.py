"""
recommendation_engine.py — Explainable recommendation structure and builder.

Phase 6 Step 1: Structural foundation only.
No rules are evaluated here yet.  Step 2 will add rule evaluators that call
``build_recommendations`` with a list of fired rules.

Design for explainability:
  - Every Recommendation carries:
      * ``rule_id``            — stable machine-readable identifier
      * ``triggered_by_value`` — the metric that fired the rule (Decimal)
      * ``threshold_value``    — the limit that was breached (Decimal)
      * ``description``        — plain-English explanation
  - The UI can render "Why?" tooltips from these fields without any
    additional database queries.

The ``RecommendationEngine`` class is stateless and instantiated fresh for
each analysis run.  It accumulates recommendations in order of priority
(CRITICAL → HIGH → MEDIUM → LOW) so consumers can take the top-N.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Optional

from .contracts import (
    Recommendation,
    RecommendationCategory,
    RecommendationPriority,
)

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Collects and sorts Recommendation objects for a single analysis run.

    Usage pattern (to be wired in Step 2):
    ----------------------------------------
    engine = RecommendationEngine(business_id=ctx.business_id)

    # Rule evaluators call engine.add() when a rule fires:
    engine.add(
        rule_id="low_gross_margin",
        title="Gross margin below target",
        description=(
            "Your gross margin is 18 %, below the 30 % target.  "
            "Review product pricing or reduce COGS."
        ),
        priority=RecommendationPriority.HIGH,
        category=RecommendationCategory.FINANCE,
        triggered_by_value=Decimal("18.00"),
        threshold_value=Decimal("30.00"),
        action_url="/analytics/pl/",
    )

    recommendations = engine.get_sorted()
    """

    # Priority ordering for sort (lower number = higher urgency)
    _PRIORITY_ORDER = {
        RecommendationPriority.CRITICAL: 0,
        RecommendationPriority.HIGH: 1,
        RecommendationPriority.MEDIUM: 2,
        RecommendationPriority.LOW: 3,
    }

    def __init__(self, business_id: int) -> None:
        self._business_id = business_id
        self._items: List[Recommendation] = []

    def add(
        self,
        *,
        rule_id: str,
        title: str,
        description: str,
        priority: RecommendationPriority,
        category: RecommendationCategory,
        triggered_by_value: Optional[Decimal] = None,
        threshold_value: Optional[Decimal] = None,
        action_url: str = "",
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Record a single fired recommendation.

        All arguments are keyword-only to prevent positional ordering bugs
        when new optional fields are added in future steps.
        """
        rec = Recommendation(
            title=title,
            description=description,
            priority=priority,
            category=category,
            rule_id=rule_id,
            triggered_by_value=triggered_by_value,
            threshold_value=threshold_value,
            action_url=action_url,
            metadata=metadata or {},
        )
        self._items.append(rec)

        logger.debug(
            "recommendation_engine: business_id=%d rule_id=%s priority=%s",
            self._business_id,
            rule_id,
            priority.value,
        )

    def get_sorted(self) -> List[Recommendation]:
        """
        Return all accumulated recommendations sorted by priority (CRITICAL first).

        Within the same priority tier, insertion order is preserved so rules
        with higher certainty (added first by convention) appear before lower-
        certainty ones.
        """
        return sorted(
            self._items,
            key=lambda r: self._PRIORITY_ORDER.get(r.priority, 99),
        )

    def count(self) -> int:
        """Return the number of recommendations collected so far."""
        return len(self._items)

    def clear(self) -> None:
        """Reset the engine for reuse (mainly useful in tests)."""
        self._items = []
