"""
inference.py — Future ML inference pipeline boundary.

Phase 6 Step 1: Extension boundary only.
No ML libraries are imported.  No predictions are generated.
Scikit-learn is NOT a dependency at this phase.

This module defines the interface that a future inference pipeline must
implement.  Callers should use these functions rather than calling
model_registry.ModelDescriptor.load() directly so that the inference
contract is stable across V1 → V2.

Extension guide (Phase 8 / V2):
---------------------------------
1. Implement ``predict_demand`` and ``predict_optimal_price`` with real
   estimators obtained from model_registry.get_registry().get(model_id).load().
2. Return the typed result dataclasses defined below.
3. No callers change — the function signatures are stable.

IMPORTANT: Do NOT add ``import sklearn`` or any ML library import here.
           This file must remain importable without additional dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InferenceNotImplementedError(NotImplementedError):
    """
    Raised by placeholder inference functions until Phase 8 (V2).

    Distinguishable from generic NotImplementedError so tests can assert
    specifically on this exception type.
    """


class ModelNotFoundError(Exception):
    """
    Raised when inference is requested for a model that has not been trained
    and registered in the ModelRegistry.
    """


# ---------------------------------------------------------------------------
# Inference result types
# ---------------------------------------------------------------------------


@dataclass
class DemandForecast:
    """
    Point forecast for product demand over a future horizon.

    All quantity values are integers (units).  Confidence bounds are provided
    as Decimal percentages for display (e.g. Decimal("80.00") = 80 % CI).
    """

    product_id: int
    business_id: int
    horizon_days: int              # Number of days ahead the forecast covers
    predicted_units: int           # Point estimate
    lower_bound: Optional[int] = None  # Lower confidence bound
    upper_bound: Optional[int] = None  # Upper confidence bound
    confidence_pct: Optional[Decimal] = None  # e.g. Decimal("80.00")
    model_version: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PriceRecommendation:
    """
    Optimal price recommendation for a single product.

    All monetary values are Decimal.
    """

    product_id: int
    business_id: int
    current_price: Optional[Decimal]       # Product.selling_price at inference time
    recommended_price: Optional[Decimal]   # Model recommendation
    expected_revenue_change_pct: Optional[Decimal]  # vs. current price
    model_version: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public inference boundary functions
# ---------------------------------------------------------------------------


def predict_demand(
    business_id: int,
    product_id: int,
    horizon_days: int = 30,
) -> DemandForecast:
    """
    Predict future product demand for the given business and product.

    STUB — raises InferenceNotImplementedError until Phase 8 (V2).

    Args:
        business_id:  PK of the Business.
        product_id:   PK of the Product to forecast.
        horizon_days: Number of future days to forecast (default 30).

    Returns:
        DemandForecast with predicted_units and confidence bounds.

    Raises:
        ModelNotFoundError
            If no trained demand-forecast model is registered.
        InferenceNotImplementedError
            Until Phase 8.
    """
    logger.debug(
        "inference.predict_demand: business_id=%d product_id=%d — NOT IMPLEMENTED",
        business_id,
        product_id,
    )
    raise InferenceNotImplementedError(
        "Demand prediction is not implemented in Phase 6. "
        "This will be available in Phase 8 once ≥60 days of sales data "
        "have been collected and a model has been trained."
    )


def predict_optimal_price(
    business_id: int,
    product_id: int,
) -> PriceRecommendation:
    """
    Recommend an optimal selling price for the given product.

    STUB — raises InferenceNotImplementedError until Phase 8 (V2).

    Args:
        business_id: PK of the Business.
        product_id:  PK of the Product to optimise.

    Returns:
        PriceRecommendation with recommended_price and expected revenue impact.

    Raises:
        ModelNotFoundError
            If no trained price-optimisation model is registered.
        InferenceNotImplementedError
            Until Phase 8.
    """
    logger.debug(
        "inference.predict_optimal_price: business_id=%d product_id=%d — NOT IMPLEMENTED",
        business_id,
        product_id,
    )
    raise InferenceNotImplementedError(
        "Price optimisation is not implemented in Phase 6. "
        "This will be available in Phase 8 once ≥60 days of sales data "
        "have been collected and a model has been trained."
    )
