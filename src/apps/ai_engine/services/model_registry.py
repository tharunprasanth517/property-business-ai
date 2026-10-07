"""
model_registry.py — Future ML model registration boundary.

Phase 6 Step 1: Extension boundary only.
No ML libraries are imported.  No models are trained or loaded.
Scikit-learn is NOT a dependency at this phase.

This module defines the interface that a future ML model registry must
implement so that the inference layer can swap between rule-based (V1)
and ML (V2) implementations without changing callers.

Extension guide (Phase 8 / V2):
---------------------------------
1. Install scikit-learn in requirements/base.txt.
2. Implement ``register`` and ``get`` against a real storage backend
   (Django model, filesystem, MLflow, etc.).
3. Implement ``ModelDescriptor.load()`` to deserialise a fitted estimator.
4. No other files need to change — the boundary is already wired.

IMPORTANT: Do NOT add ``import sklearn`` or any ML library here.
           This file must remain importable with zero extra dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model descriptor (metadata only — no serialised estimator in Step 1)
# ---------------------------------------------------------------------------


@dataclass
class ModelDescriptor:
    """
    Metadata record for a registered ML model.

    In V2 this will be backed by a database row or MLflow run.
    In Step 1 it is an in-memory placeholder.

    Attributes
    ----------
    model_id    : Unique stable string identifier, e.g. "demand_forecast_v1".
    version     : Semver string, e.g. "1.0.0".
    description : Human-readable description of what the model predicts.
    features    : Ordered list of feature names the model expects as input.
    target      : The quantity the model predicts, e.g. "weekly_sales_units".
    created_at  : Timestamp the model was registered.
    is_active   : Whether this version should be used for inference.
    metadata    : Arbitrary key→value store for hyperparameters, metrics, etc.
    """

    model_id: str
    version: str
    description: str
    features: List[str] = field(default_factory=list)
    target: str = ""
    created_at: Optional[datetime] = None
    is_active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def load(self) -> Any:
        """
        Deserialise and return the fitted estimator.

        STUB — raises NotImplementedError until V2.
        In V2: unpickle from filesystem / cloud storage / MLflow artifacts.
        """
        raise NotImplementedError(
            f"ModelDescriptor.load() is not implemented for model '{self.model_id}'. "
            "ML model loading will be available in Phase 8 (V2)."
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ModelRegistry:
    """
    In-memory model registry (Phase 6 placeholder).

    V2 will replace the in-memory dict with a database-backed store so that
    model versions survive process restarts and can be promoted/demoted
    without code changes.

    The registry is a module-level singleton accessed via ``get_registry()``.
    Do NOT instantiate ModelRegistry directly in production code.
    """

    def __init__(self) -> None:
        self._models: Dict[str, ModelDescriptor] = {}

    def register(self, descriptor: ModelDescriptor) -> None:
        """
        Register a model descriptor.

        If a descriptor with the same model_id already exists it is
        overwritten (last-writer-wins).  In V2 this will require an
        explicit version bump.
        """
        self._models[descriptor.model_id] = descriptor
        logger.info(
            "model_registry.register: model_id=%s version=%s",
            descriptor.model_id,
            descriptor.version,
        )

    def get(self, model_id: str) -> Optional[ModelDescriptor]:
        """Return the registered descriptor for model_id, or None."""
        return self._models.get(model_id)

    def list_active(self) -> List[ModelDescriptor]:
        """Return all descriptors where is_active=True."""
        return [d for d in self._models.values() if d.is_active]

    def count(self) -> int:
        """Return the total number of registered descriptors."""
        return len(self._models)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_REGISTRY: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """
    Return the shared ModelRegistry singleton.

    Thread-safety note: In V1 (single-process Django with no ML loading)
    this is safe.  In V2 with concurrent model loading, use a lock or
    replace with a database-backed implementation.

    Testing note: This function returns a process-level singleton, so
    registrations from one test will bleed into subsequent tests if
    get_registry() is called directly.  In test code, always instantiate
    ``ModelRegistry()`` directly for fully isolated state:

        registry = ModelRegistry()   # isolated, not the singleton
        registry.register(descriptor)
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ModelRegistry()
    return _REGISTRY
