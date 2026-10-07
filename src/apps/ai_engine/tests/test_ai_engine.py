"""
Phase 6 Step 1 — ai_engine test suite.

Coverage:
  1. App imports correctly and Django recognises it.
  2. All service modules can be imported without error.
  3. Contracts (DTOs) can be instantiated correctly.
  4. RecommendationEngine accumulates and sorts correctly.
  5. ModelRegistry registers and retrieves descriptors.
  6. Training stubs raise correct exceptions.
  7. Inference stubs raise correct exceptions.
  8. Context helpers enforce tenant isolation:
       - Unauthenticated user → PermissionDenied
       - Wrong business_id → Http404
       - Wrong property_id → Http404
       - Cross-tenant property_id → Http404
  9. Feature extraction returns correct Decimal types and no cross-tenant data.
  10. No existing Phase 1–5 tests regressed (run via manage.py test).

Note: Tests that require database access subclass django.test.TestCase.
      Pure-Python unit tests subclass unittest.TestCase to stay fast.
"""

from datetime import date
from decimal import Decimal
from unittest import TestCase as PureTestCase

from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TestCase
from django.contrib.auth import get_user_model


# ---------------------------------------------------------------------------
# Helper: minimal business + user fixtures
# ---------------------------------------------------------------------------


def _create_user(username, email, password="StrongPass123!"):
    User = get_user_model()
    return User.objects.create_user(
        username=username, email=email, password=password
    )


def _create_business_with_owner(user, name):
    from apps.businesses.models import Business, BusinessUser

    business = Business.objects.create(name=name, owner=user)
    BusinessUser.objects.create(
        business=business, user=user, role=BusinessUser.Role.OWNER
    )
    return business


# ===========================================================================
# 1. App registration
# ===========================================================================


class AiEngineAppRegistrationTests(PureTestCase):
    """Verify Django recognises apps.ai_engine."""

    def test_app_is_in_installed_apps(self):
        app_config = apps.get_app_config("ai_engine")
        self.assertIsNotNone(app_config)

    def test_app_label(self):
        app_config = apps.get_app_config("ai_engine")
        self.assertEqual(app_config.label, "ai_engine")

    def test_app_name(self):
        app_config = apps.get_app_config("ai_engine")
        self.assertEqual(app_config.name, "apps.ai_engine")

    def test_app_verbose_name(self):
        app_config = apps.get_app_config("ai_engine")
        self.assertEqual(app_config.verbose_name, "AI Engine")


# ===========================================================================
# 2. Service module imports
# ===========================================================================


class AiEngineModuleImportTests(PureTestCase):
    """All service modules must be importable without error."""

    def test_contracts_importable(self):
        from apps.ai_engine.services import contracts  # noqa: F401

    def test_context_importable(self):
        from apps.ai_engine.services import context  # noqa: F401

    def test_feature_extraction_importable(self):
        from apps.ai_engine.services import feature_extraction  # noqa: F401

    def test_property_analysis_importable(self):
        from apps.ai_engine.services import property_analysis  # noqa: F401

    def test_property_rules_importable(self):
        from apps.ai_engine.services import property_rules  # noqa: F401

    def test_business_rules_importable(self):
        from apps.ai_engine.services import business_rules  # noqa: F401

    def test_business_analysis_importable(self):
        from apps.ai_engine.services import business_analysis  # noqa: F401

    def test_recommendation_engine_importable(self):
        from apps.ai_engine.services import recommendation_engine  # noqa: F401

    def test_model_registry_importable(self):
        from apps.ai_engine.services import model_registry  # noqa: F401

    def test_training_importable(self):
        from apps.ai_engine.services import training  # noqa: F401

    def test_inference_importable(self):
        from apps.ai_engine.services import inference  # noqa: F401


# ===========================================================================
# 3. Contract (DTO) instantiation
# ===========================================================================


class ContractInstantiationTests(PureTestCase):
    """DTOs must be instantiable and carry correct field types."""

    def test_property_features_basic(self):
        from apps.ai_engine.services.contracts import PropertyFeatures

        pf = PropertyFeatures(
            property_id=1,
            business_id=2,
            property_name="Test Plot",
            property_type="LAND",
            ownership_status="OWNED",
            development_status="RAW",
            purchase_price=Decimal("100000.00"),
        )
        self.assertEqual(pf.property_id, 1)
        self.assertIsInstance(pf.purchase_price, Decimal)
        self.assertIsNone(pf.current_roi_pct)

    def test_business_features_basic(self):
        from apps.ai_engine.services.contracts import BusinessFeatures

        bf = BusinessFeatures(business_id=1, business_name="Acme Ltd")
        self.assertIsNone(bf.revenue)
        self.assertIsNone(bf.gross_margin_pct)

    def test_property_analysis_result_defaults(self):
        from apps.ai_engine.services.contracts import (
            AnalysisStatus,
            PropertyAnalysisResult,
        )

        result = PropertyAnalysisResult(
            property_id=1,
            business_id=2,
            status=AnalysisStatus.OK,
        )
        self.assertEqual(result.status, AnalysisStatus.OK)
        self.assertIsNone(result.investment_score)
        self.assertEqual(result.recommendations, [])

    def test_business_analysis_result_defaults(self):
        from apps.ai_engine.services.contracts import (
            AnalysisStatus,
            BusinessAnalysisResult,
        )

        result = BusinessAnalysisResult(
            business_id=1,
            status=AnalysisStatus.OK,
        )
        self.assertIsNone(result.health_score)
        self.assertEqual(result.score_breakdown, {})

    def test_recommendation_dto(self):
        from apps.ai_engine.services.contracts import (
            Recommendation,
            RecommendationCategory,
            RecommendationPriority,
        )

        rec = Recommendation(
            title="Low margin",
            description="Gross margin is below 30 %.",
            priority=RecommendationPriority.HIGH,
            category=RecommendationCategory.FINANCE,
            rule_id="low_gross_margin",
            triggered_by_value=Decimal("18.00"),
            threshold_value=Decimal("30.00"),
        )
        self.assertIsInstance(rec.triggered_by_value, Decimal)
        self.assertEqual(rec.rule_id, "low_gross_margin")


# ===========================================================================
# 4. RecommendationEngine
# ===========================================================================


class RecommendationEngineTests(PureTestCase):
    """Engine accumulates and sorts by priority correctly."""

    def _make_engine(self):
        from apps.ai_engine.services.recommendation_engine import RecommendationEngine

        return RecommendationEngine(business_id=1)

    def test_empty_engine_returns_empty_list(self):
        engine = self._make_engine()
        self.assertEqual(engine.get_sorted(), [])

    def test_recommendations_sorted_critical_first(self):
        from apps.ai_engine.services.contracts import (
            RecommendationCategory,
            RecommendationPriority,
        )

        engine = self._make_engine()
        engine.add(
            rule_id="low_stock",
            title="Low stock",
            description="Stock below reorder level.",
            priority=RecommendationPriority.MEDIUM,
            category=RecommendationCategory.INVENTORY,
        )
        engine.add(
            rule_id="cash_flow_crisis",
            title="Cash flow crisis",
            description="Net profit is deeply negative.",
            priority=RecommendationPriority.CRITICAL,
            category=RecommendationCategory.FINANCE,
        )
        engine.add(
            rule_id="review_pricing",
            title="Review pricing",
            description="Margin below 30 %.",
            priority=RecommendationPriority.HIGH,
            category=RecommendationCategory.FINANCE,
        )

        sorted_recs = engine.get_sorted()
        self.assertEqual(len(sorted_recs), 3)
        self.assertEqual(sorted_recs[0].rule_id, "cash_flow_crisis")
        self.assertEqual(sorted_recs[1].rule_id, "review_pricing")
        self.assertEqual(sorted_recs[2].rule_id, "low_stock")

    def test_count(self):
        from apps.ai_engine.services.contracts import (
            RecommendationCategory,
            RecommendationPriority,
        )

        engine = self._make_engine()
        engine.add(
            rule_id="r1",
            title="R1",
            description="",
            priority=RecommendationPriority.LOW,
            category=RecommendationCategory.OPERATIONS,
        )
        self.assertEqual(engine.count(), 1)

    def test_clear_resets_engine(self):
        from apps.ai_engine.services.contracts import (
            RecommendationCategory,
            RecommendationPriority,
        )

        engine = self._make_engine()
        engine.add(
            rule_id="r1",
            title="R1",
            description="",
            priority=RecommendationPriority.LOW,
            category=RecommendationCategory.OPERATIONS,
        )
        engine.clear()
        self.assertEqual(engine.count(), 0)


# ===========================================================================
# 5. ModelRegistry
# ===========================================================================


class ModelRegistryTests(PureTestCase):
    """Registry registers and retrieves descriptors; load() raises NotImplementedError."""

    def _make_registry(self):
        from apps.ai_engine.services.model_registry import ModelRegistry

        return ModelRegistry()

    def test_register_and_get(self):
        from apps.ai_engine.services.model_registry import ModelDescriptor

        registry = self._make_registry()
        desc = ModelDescriptor(
            model_id="demand_forecast_v1",
            version="1.0.0",
            description="Demand forecasting model",
        )
        registry.register(desc)
        retrieved = registry.get("demand_forecast_v1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.version, "1.0.0")

    def test_get_nonexistent_returns_none(self):
        registry = self._make_registry()
        self.assertIsNone(registry.get("nonexistent_model"))

    def test_list_active_filters_correctly(self):
        from apps.ai_engine.services.model_registry import ModelDescriptor

        registry = self._make_registry()
        registry.register(
            ModelDescriptor(
                model_id="m1",
                version="1.0.0",
                description="Active",
                is_active=True,
            )
        )
        registry.register(
            ModelDescriptor(
                model_id="m2",
                version="1.0.0",
                description="Inactive",
                is_active=False,
            )
        )
        active = registry.list_active()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].model_id, "m1")

    def test_descriptor_load_raises_not_implemented(self):
        from apps.ai_engine.services.model_registry import ModelDescriptor

        desc = ModelDescriptor(model_id="m1", version="1.0.0", description="")
        with self.assertRaises(NotImplementedError):
            desc.load()


# ===========================================================================
# 6. Training stubs
# ===========================================================================


class TrainingStubTests(PureTestCase):
    """Training functions must raise TrainingNotImplementedError."""

    def test_train_demand_forecast_raises(self):
        from apps.ai_engine.services.training import (
            TrainingNotImplementedError,
            train_demand_forecast,
        )

        with self.assertRaises(TrainingNotImplementedError):
            train_demand_forecast(business_id=1)

    def test_train_price_optimiser_raises(self):
        from apps.ai_engine.services.training import (
            TrainingNotImplementedError,
            train_price_optimiser,
        )

        with self.assertRaises(TrainingNotImplementedError):
            train_price_optimiser(business_id=1)

    def test_check_training_readiness_insufficient(self):
        from apps.ai_engine.services.training import check_training_readiness

        self.assertFalse(check_training_readiness(0))
        self.assertFalse(check_training_readiness(59))

    def test_check_training_readiness_sufficient(self):
        from apps.ai_engine.services.training import check_training_readiness

        self.assertTrue(check_training_readiness(60))
        self.assertTrue(check_training_readiness(365))


# ===========================================================================
# 7. Inference stubs
# ===========================================================================


class InferenceStubTests(PureTestCase):
    """Inference functions must raise InferenceNotImplementedError."""

    def test_predict_demand_raises(self):
        from apps.ai_engine.services.inference import (
            InferenceNotImplementedError,
            predict_demand,
        )

        with self.assertRaises(InferenceNotImplementedError):
            predict_demand(business_id=1, product_id=1)

    def test_predict_optimal_price_raises(self):
        from apps.ai_engine.services.inference import (
            InferenceNotImplementedError,
            predict_optimal_price,
        )

        with self.assertRaises(InferenceNotImplementedError):
            predict_optimal_price(business_id=1, product_id=1)


# ===========================================================================
# 8. Context helper tenant isolation (requires DB)
# ===========================================================================


class ContextTenantIsolationTests(TestCase):
    """Context helpers must enforce strict tenant boundaries."""

    def setUp(self):
        self.user = _create_user("ctx-owner", "ctx-owner@example.com")
        self.other_user = _create_user("ctx-other", "ctx-other@example.com")
        self.business = _create_business_with_owner(self.user, "Context Holdings")
        self.other_business = _create_business_with_owner(
            self.other_user, "Other Context Holdings"
        )

    def test_get_business_context_authenticated_user_returns_correct_business(self):
        from apps.ai_engine.services.context import get_business_context

        ctx = get_business_context(self.user, business_id=self.business.pk)
        self.assertEqual(ctx.business_id, self.business.pk)
        self.assertEqual(ctx.business.pk, self.business.pk)
        self.assertEqual(ctx.user, self.user)

    def test_get_business_context_unauthenticated_raises_permission_denied(self):
        from apps.ai_engine.services.context import get_business_context
        from unittest.mock import MagicMock

        anon = MagicMock()
        anon.is_authenticated = False

        with self.assertRaises(PermissionDenied):
            get_business_context(anon, business_id=self.business.pk)

    def test_get_business_context_wrong_business_id_raises_404(self):
        from apps.ai_engine.services.context import get_business_context

        with self.assertRaises(Http404):
            get_business_context(self.user, business_id=self.other_business.pk)

    def test_get_business_context_no_business_id_returns_first(self):
        from apps.ai_engine.services.context import get_business_context

        ctx = get_business_context(self.user)
        self.assertIsNotNone(ctx.business)
        self.assertEqual(ctx.user, self.user)

    def test_get_property_context_cross_tenant_raises_404(self):
        from apps.ai_engine.services.context import get_property_context
        from apps.businesses.models import Property

        other_property = Property.objects.create(
            business=self.other_business,
            owner=self.other_user,
            name="Private Cross-Tenant Property",
        )
        # self.user should NOT be able to access other_property
        with self.assertRaises(Http404):
            get_property_context(self.user, property_id=other_property.pk)

    def test_get_property_context_valid_access(self):
        from apps.ai_engine.services.context import get_property_context
        from apps.businesses.models import Property

        prop = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Own Property",
        )
        ctx = get_property_context(self.user, property_id=prop.pk)
        self.assertEqual(ctx.property_id, prop.pk)
        self.assertEqual(ctx.business_id, self.business.pk)

    def test_get_property_context_unauthenticated_raises_permission_denied(self):
        from apps.ai_engine.services.context import get_property_context
        from apps.businesses.models import Property
        from unittest.mock import MagicMock

        anon = MagicMock()
        anon.is_authenticated = False

        prop = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Property For Anon Test",
        )
        with self.assertRaises(PermissionDenied):
            get_property_context(anon, property_id=prop.pk)


# ===========================================================================
# 9. Feature extraction — correct types and tenant isolation
# ===========================================================================


class FeatureExtractionTests(TestCase):
    """Feature extraction must return correct Decimal types and honour tenant scope."""

    def setUp(self):
        from apps.businesses.models import Property

        self.user = _create_user("feat-owner", "feat-owner@example.com")
        self.other_user = _create_user("feat-other", "feat-other@example.com")
        self.business = _create_business_with_owner(self.user, "Feature Holdings")
        self.other_business = _create_business_with_owner(
            self.other_user, "Other Feature Holdings"
        )
        self.property = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Feature Property",
            purchase_price=Decimal("500000.00"),
            current_estimated_value=Decimal("600000.00"),
            expected_selling_price=Decimal("700000.00"),
            purchase_date=date(2025, 1, 1),
        )

    def test_property_features_purchase_price_is_decimal(self):
        from apps.ai_engine.services.context import get_property_context
        from apps.ai_engine.services.feature_extraction import extract_property_features

        ctx = get_property_context(self.user, property_id=self.property.pk)
        features = extract_property_features(ctx)
        self.assertIsInstance(features.purchase_price, Decimal)
        self.assertEqual(features.purchase_price, Decimal("500000.00"))

    def test_property_features_total_invested_decimal(self):
        from apps.ai_engine.services.context import get_property_context
        from apps.ai_engine.services.feature_extraction import extract_property_features

        ctx = get_property_context(self.user, property_id=self.property.pk)
        features = extract_property_features(ctx)
        # No expenses or loans added, so total_invested == purchase_price
        self.assertIsInstance(features.total_invested, Decimal)
        self.assertEqual(features.total_invested, Decimal("500000.00"))

    def test_property_features_roi_is_decimal(self):
        from apps.ai_engine.services.context import get_property_context
        from apps.ai_engine.services.feature_extraction import extract_property_features

        ctx = get_property_context(self.user, property_id=self.property.pk)
        features = extract_property_features(ctx)
        # current_pnl = 600000 - 500000 = 100000
        # roi = 100000/500000*100 = 20.00
        self.assertIsInstance(features.current_roi_pct, Decimal)
        self.assertEqual(features.current_roi_pct, Decimal("20.00"))

    def test_property_features_days_held_computed(self):
        from apps.ai_engine.services.context import get_property_context
        from apps.ai_engine.services.feature_extraction import extract_property_features

        ctx = get_property_context(self.user, property_id=self.property.pk)
        features = extract_property_features(ctx)
        self.assertIsNotNone(features.days_held)
        self.assertGreater(features.days_held, 0)

    def test_property_features_no_cross_tenant_data(self):
        """Feature extraction must never return data from another business."""
        from apps.businesses.models import Property
        from apps.finances.models import PropertyExpense
        from apps.ai_engine.services.context import get_property_context
        from apps.ai_engine.services.feature_extraction import extract_property_features

        # Expense on the OTHER business's property
        other_prop = Property.objects.create(
            business=self.other_business,
            owner=self.other_user,
            name="Other Feature Property",
        )
        PropertyExpense.objects.create(
            business=self.other_business,
            property=other_prop,
            title="Cross-tenant expense",
            amount=Decimal("99999.00"),
            expense_date=date(2025, 6, 1),
        )

        # Extracting features for our own property must not pick up other business's expenses
        ctx = get_property_context(self.user, property_id=self.property.pk)
        features = extract_property_features(ctx)
        # total_expenses should be None (no expenses on self.property)
        self.assertIsNone(features.total_expenses)

    def test_business_features_revenue_is_decimal(self):
        from apps.transactions.models import Sale
        from apps.ai_engine.services.context import get_business_context
        from apps.ai_engine.services.feature_extraction import extract_business_features

        Sale.objects.create(
            business=self.business,
            customer_name="Customer A",
            sale_date=date(2026, 1, 10),
            total_amount=Decimal("12000.00"),
        )
        ctx = get_business_context(self.user, business_id=self.business.pk)
        features = extract_business_features(ctx)
        self.assertIsInstance(features.revenue, Decimal)
        self.assertEqual(features.revenue, Decimal("12000.00"))

    def test_business_features_cross_tenant_isolation(self):
        """BusinessFeatures must only aggregate data for the requested business."""
        from apps.transactions.models import Sale
        from apps.ai_engine.services.context import get_business_context
        from apps.ai_engine.services.feature_extraction import extract_business_features

        # Sale on other business — must NOT appear in our features
        Sale.objects.create(
            business=self.other_business,
            customer_name="Other Customer",
            sale_date=date(2026, 1, 15),
            total_amount=Decimal("999999.00"),
        )
        ctx = get_business_context(self.user, business_id=self.business.pk)
        features = extract_business_features(ctx)
        # Our business has no sales yet
        self.assertIsNone(features.revenue)


# ===========================================================================
# 10. End-to-end pipeline: analyse_property / analyse_business
# ===========================================================================


class AnalysisPipelineTests(TestCase):
    """analyse_property and analyse_business return correct result types."""

    def setUp(self):
        from apps.businesses.models import Property

        self.user = _create_user("pipe-owner", "pipe-owner@example.com")
        self.other_user = _create_user("pipe-other", "pipe-other@example.com")
        self.business = _create_business_with_owner(self.user, "Pipeline Holdings")
        self.other_business = _create_business_with_owner(
            self.other_user, "Other Pipeline Holdings"
        )
        self.property = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Pipeline Property",
            purchase_price=Decimal("200000.00"),
            current_estimated_value=Decimal("250000.00"),
        )

    def test_analyse_property_returns_ok_result(self):
        from apps.ai_engine.services.property_analysis import analyse_property
        from apps.ai_engine.services.contracts import AnalysisStatus

        result = analyse_property(self.user, property_id=self.property.pk)
        self.assertEqual(result.status, AnalysisStatus.OK)
        self.assertEqual(result.property_id, self.property.pk)
        self.assertEqual(result.business_id, self.business.pk)
        self.assertIsNotNone(result.features)

    def test_analyse_property_cross_tenant_raises_404(self):
        from apps.ai_engine.services.property_analysis import analyse_property
        from apps.businesses.models import Property

        other_prop = Property.objects.create(
            business=self.other_business,
            owner=self.other_user,
            name="Cross-Tenant Pipeline Property",
        )
        with self.assertRaises(Http404):
            analyse_property(self.user, property_id=other_prop.pk)

    def test_analyse_business_returns_ok_result(self):
        from apps.ai_engine.services.business_analysis import analyse_business
        from apps.ai_engine.services.contracts import AnalysisStatus

        result = analyse_business(self.user, business_id=self.business.pk)
        self.assertEqual(result.status, AnalysisStatus.OK)
        self.assertEqual(result.business_id, self.business.pk)
        self.assertIsNone(result.health_score)   # Step 2 placeholder
        self.assertIsNotNone(result.features)

    def test_analyse_business_cross_tenant_raises_404(self):
        from apps.ai_engine.services.business_analysis import analyse_business

        with self.assertRaises(Http404):
            analyse_business(self.user, business_id=self.other_business.pk)

    def test_analyse_property_investment_score_is_none(self):
        """Step 1 must not compute scores — they are reserved for Step 2."""
        from apps.ai_engine.services.property_analysis import analyse_property

        result = analyse_property(self.user, property_id=self.property.pk)
        self.assertIsNone(result.investment_score)
        self.assertEqual(result.recommendations, [])
        self.assertEqual(result.insights, [])

    def test_analyse_business_health_score_is_none(self):
        """Step 1 must not compute health score — reserved for Step 2."""
        from apps.ai_engine.services.business_analysis import analyse_business

        result = analyse_business(self.user, business_id=self.business.pk)
        self.assertIsNone(result.health_score)
        self.assertEqual(result.score_breakdown, {})
        self.assertEqual(result.recommendations, [])


# ===========================================================================
# 11. Additional context / pipeline edge-case coverage
# ===========================================================================


class ContextEdgeCaseTests(TestCase):
    """Edge cases not covered by the primary context and pipeline tests."""

    def setUp(self):
        self.user = _create_user("edge-owner", "edge-owner@example.com")
        self.business = _create_business_with_owner(self.user, "Edge Holdings")

    def test_analyse_property_nonexistent_id_raises_404(self):
        """
        analyse_property with a completely non-existent property_id must
        raise Http404 (not PermissionDenied or any other exception).
        """
        from apps.ai_engine.services.property_analysis import analyse_property

        with self.assertRaises(Http404):
            analyse_property(self.user, property_id=999999)

    def test_get_business_context_no_businesses_raises_permission_denied(self):
        """
        An authenticated user who belongs to no businesses must receive
        PermissionDenied (not Http404) when calling get_business_context
        with business_id=None.
        """
        from apps.ai_engine.services.context import get_business_context

        # Create a user who has never been added to any business
        isolated_user = _create_user("no-biz-user", "no-biz@example.com")

        with self.assertRaises(PermissionDenied):
            get_business_context(isolated_user, business_id=None)
