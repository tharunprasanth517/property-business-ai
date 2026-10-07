"""
training.py — Future ML training pipeline boundary.

Phase 6 Step 1: Extension boundary only.
No ML libraries are imported.  No models are trained.
Scikit-learn is NOT a dependency at this phase.

This module defines the interface that a future training pipeline must
implement.  It is structured so that V2 can fill in ``train_demand_forecast``
and ``train_price_optimiser`` without changing any callers.

Extension guide (Phase 8 / V2):
---------------------------------
1. Install scikit-learn (and optionally pandas, joblib) in requirements.
2. Implement the functions below against real estimators.
3. Persist trained models via model_registry.ModelDescriptor + a storage
   backend.
4. Enforce the minimum-data guard (MIN_TRAINING_DAYS) to prevent
   training on insufficient history — the placeholder already raises
   InsufficientDataError so callers are already protected.

IMPORTANT: Do NOT add ``import sklearn``, ``import pandas``, or any ML
           library import here.  This file must remain importable without
           additional dependencies.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants (configurable in V2 via Django settings)
# ---------------------------------------------------------------------------

MIN_TRAINING_DAYS: int = 60
"""
Minimum number of distinct transaction days required before training is
attempted.  60 days provides enough seasonal variation for a basic time-
series regression.  Adjust in Django settings in V2.
"""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InsufficientDataError(Exception):
    """
    Raised when there is not enough historical data to train a model.

    Callers should catch this exception and surface a user-friendly message
    rather than letting it propagate as a 500 error.
    """


class TrainingNotImplementedError(NotImplementedError):
    """
    Raised by placeholder training functions until V2 is implemented.

    Distinguishable from generic NotImplementedError so tests can assert
    specifically on this exception type.
    """


# ---------------------------------------------------------------------------
# Public training boundary functions
# ---------------------------------------------------------------------------


def train_demand_forecast(
    business_id: int,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> None:
    """
    Train a demand forecasting model for the given business.

    STUB — raises TrainingNotImplementedError until Phase 8 (V2).

    Args:
        business_id: PK of the Business to train for.
        date_from:   Start of the training window (inclusive).
        date_to:     End of the training window (inclusive).

    Raises:
        TrainingNotImplementedError
            Always, until Phase 8.  (InsufficientDataError is NOT raised here
            yet — readiness validation via check_training_readiness() will be
            wired into this function in Phase 8 before training is attempted.)
    """
    logger.debug(
        "training.train_demand_forecast: business_id=%d — NOT IMPLEMENTED (Phase 8)",
        business_id,
    )
    raise TrainingNotImplementedError(
        "Demand forecasting model training is not implemented in Phase 6. "
        f"Requires ≥{MIN_TRAINING_DAYS} days of transaction history and "
        "Phase 8 (scikit-learn integration)."
    )


def train_price_optimiser(
    business_id: int,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> None:
    """
    Train a price optimisation model for the given business.

    STUB — raises TrainingNotImplementedError until Phase 8 (V2).

    Args:
        business_id: PK of the Business to train for.
        date_from:   Start of the training window (inclusive).
        date_to:     End of the training window (inclusive).

    Raises:
        TrainingNotImplementedError
            Always, until Phase 8.  (InsufficientDataError is NOT raised here
            yet — readiness validation via check_training_readiness() will be
            wired into this function in Phase 8 before training is attempted.)
    """
    logger.debug(
        "training.train_price_optimiser: business_id=%d — NOT IMPLEMENTED (Phase 8)",
        business_id,
    )
    raise TrainingNotImplementedError(
        "Price optimisation model training is not implemented in Phase 6. "
        f"Requires ≥{MIN_TRAINING_DAYS} days of transaction history and "
        "Phase 8 (scikit-learn integration)."
    )


def check_training_readiness(transaction_days: int) -> bool:
    """
    Return True if there is enough historical data to attempt ML training.

    Args:
        transaction_days: Number of distinct days on which any transaction
                          occurred (from BusinessFeatures.transaction_days).

    Returns:
        True if transaction_days >= MIN_TRAINING_DAYS, False otherwise.
    """
    return transaction_days >= MIN_TRAINING_DAYS
