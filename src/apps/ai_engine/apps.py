"""
AppConfig for the ai_engine application.

Phase 6: AI/Intelligence layer foundation.

V1: Rule-based business intelligence engine — computes Business Health
    Scores and generates prioritised, explainable action plans from
    existing operational data.

V2 (future, ≥60 days of data): Machine learning prediction pipeline
    (Scikit-learn) for demand forecasting and price optimisation.

No models are declared in this app; it is a pure service layer.
"""

from django.apps import AppConfig


class AiEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_engine"
    verbose_name = "AI Engine"
