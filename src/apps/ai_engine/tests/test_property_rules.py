"""
Phase 6 Step 2 — Property intelligence rules and pipeline test suite.

Coverage:
  1. Unit tests for each deterministic rule in isolation using pure PropertyFeatures DTOs:
     - LTV underwater (>100% -> CRITICAL)
     - High LTV (80%-100% -> HIGH)
     - Safe LTV (<80% -> no LTV alert)
     - Severe negative ROI (<= -15% -> HIGH)
     - Negative ROI (-15% < ROI < 0% -> MEDIUM)
     - Positive ROI (no negative ROI alert)
     - High expense overhead (>= 25% of purchase price -> MEDIUM)
     - Moderate expense overhead (< 25% -> no alert)
     - Target selling price reached (value >= expected -> LOW)
     - Stalled development holding (>= 365 days in RAW/ON_HOLD -> LOW)
     - In-progress / developed holding (no stalled alert)
  2. Data completeness & insufficient data handling:
     - Missing both purchase price & current value -> INSUFFICIENT_DATA status
     - Missing purchase price only -> OK status + missing purchase price recommendation
     - Missing current estimated value only -> OK status + missing valuation recommendation
  3. Safe arithmetic & edge cases:
     - Zero purchase price
     - Zero current estimated value
     - Boundary values (exactly 80.00%, 100.00%, 25.00%, 365 days, -15.00%)
     - None values in all optional fields
  4. Explainability & structure:
     - Recommendation fields: rule_id, triggered_by_value, threshold_value, action_url
     - Priority sort ordering
     - Summary structure and factual correctness
  5. End-to-end integration & tenant isolation via analyse_property:
     - Full DB pipeline with loans, expenses, valuation
     - Insufficient data DB record
     - Cross-tenant access rejection (Http404)
     - Unauthenticated access rejection (PermissionDenied)
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest import TestCase as PureTestCase

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TestCase

from apps.ai_engine.services.contracts import (
    AnalysisStatus,
    PropertyFeatures,
    RecommendationCategory,
    RecommendationPriority,
)
from apps.ai_engine.services.property_rules import (
    CRITICAL_LTV_THRESHOLD,
    EXTENDED_HOLDING_DAYS_THRESHOLD,
    HIGH_EXPENSE_RATIO_THRESHOLD,
    HIGH_LTV_THRESHOLD,
    NEGATIVE_ROI_SEVERE_THRESHOLD,
    evaluate_property_rules,
)
from apps.ai_engine.services.recommendation_engine import RecommendationEngine


# ---------------------------------------------------------------------------
# Helper: create mock PropertyFeatures for pure unit tests
# ---------------------------------------------------------------------------


def _make_features(**kwargs) -> PropertyFeatures:
    defaults = {
        "property_id": 1,
        "business_id": 10,
        "property_name": "Test Property",
        "property_type": "LAND",
        "ownership_status": "OWNED",
        "development_status": "RAW",
        "purchase_price": Decimal("100000.00"),
        "current_estimated_value": Decimal("120000.00"),
        "total_invested": Decimal("100000.00"),
        "current_roi_pct": Decimal("20.00"),
    }
    defaults.update(kwargs)
    return PropertyFeatures(**defaults)


# ===========================================================================
# 1. Unit Tests: Pure Rule Evaluation (No DB)
# ===========================================================================


class PropertyRuleUnitTests(PureTestCase):
    """Test individual deterministic rules in isolation."""

    def setUp(self):
        self.engine = RecommendationEngine(business_id=10)

    # --- LTV Rules ---

    def test_ltv_underwater_triggers_critical_recommendation(self):
        features = _make_features(
            current_estimated_value=Decimal("100000.00"),
            outstanding_loan_balance=Decimal("115000.00"),
            loan_to_value_ratio=Decimal("115.00"),
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)

        self.assertEqual(status, AnalysisStatus.OK)
        recs = self.engine.get_sorted()
        underwater_recs = [r for r in recs if r.rule_id == "property_ltv_underwater"]
        self.assertEqual(len(underwater_recs), 1)

        rec = underwater_recs[0]
        self.assertEqual(rec.priority, RecommendationPriority.CRITICAL)
        self.assertEqual(rec.category, RecommendationCategory.FINANCE)
        self.assertEqual(rec.triggered_by_value, Decimal("115.00"))
        self.assertEqual(rec.threshold_value, CRITICAL_LTV_THRESHOLD)
        self.assertIn("underwater", rec.title.lower())
        self.assertIn("/finances/properties/1/loans/", rec.action_url)
        self.assertTrue(any("exceeds property value" in i for i in insights))

    def test_high_ltv_triggers_high_priority_recommendation(self):
        features = _make_features(
            current_estimated_value=Decimal("100000.00"),
            outstanding_loan_balance=Decimal("85000.00"),
            loan_to_value_ratio=Decimal("85.00"),
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)

        recs = self.engine.get_sorted()
        high_ltv_recs = [r for r in recs if r.rule_id == "property_high_ltv"]
        self.assertEqual(len(high_ltv_recs), 1)

        rec = high_ltv_recs[0]
        self.assertEqual(rec.priority, RecommendationPriority.HIGH)
        self.assertEqual(rec.category, RecommendationCategory.FINANCE)
        self.assertEqual(rec.triggered_by_value, Decimal("85.00"))
        self.assertEqual(rec.threshold_value, HIGH_LTV_THRESHOLD)

    def test_safe_ltv_does_not_trigger_ltv_recommendation(self):
        features = _make_features(
            current_estimated_value=Decimal("100000.00"),
            outstanding_loan_balance=Decimal("50000.00"),
            loan_to_value_ratio=Decimal("50.00"),
        )
        evaluate_property_rules(features, self.engine)
        recs = self.engine.get_sorted()
        ltv_recs = [r for r in recs if "ltv" in r.rule_id]
        self.assertEqual(ltv_recs, [])

    # --- Negative ROI Rules ---

    def test_severe_negative_roi_triggers_high_priority_recommendation(self):
        features = _make_features(
            purchase_price=Decimal("100000.00"),
            total_invested=Decimal("100000.00"),
            current_estimated_value=Decimal("80000.00"),
            current_roi_pct=Decimal("-20.00"),
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)

        recs = self.engine.get_sorted()
        severe_recs = [r for r in recs if r.rule_id == "property_severe_negative_roi"]
        self.assertEqual(len(severe_recs), 1)

        rec = severe_recs[0]
        self.assertEqual(rec.priority, RecommendationPriority.HIGH)
        self.assertEqual(rec.category, RecommendationCategory.PROPERTY)
        self.assertEqual(rec.triggered_by_value, Decimal("-20.00"))
        self.assertEqual(rec.threshold_value, Decimal("0.00"))
        self.assertTrue(any("unrealised loss" in i for i in insights))

    def test_moderate_negative_roi_triggers_medium_priority_recommendation(self):
        features = _make_features(
            purchase_price=Decimal("100000.00"),
            total_invested=Decimal("100000.00"),
            current_estimated_value=Decimal("95000.00"),
            current_roi_pct=Decimal("-5.00"),
        )
        evaluate_property_rules(features, self.engine)

        recs = self.engine.get_sorted()
        mod_recs = [r for r in recs if r.rule_id == "property_negative_roi"]
        self.assertEqual(len(mod_recs), 1)
        self.assertEqual(mod_recs[0].priority, RecommendationPriority.MEDIUM)

    def test_positive_roi_does_not_trigger_negative_roi_recommendation(self):
        features = _make_features(
            current_roi_pct=Decimal("15.50"),
        )
        evaluate_property_rules(features, self.engine)
        recs = self.engine.get_sorted()
        roi_recs = [r for r in recs if "roi" in r.rule_id]
        self.assertEqual(roi_recs, [])

    # --- Expense Burden Rules ---

    def test_high_expense_overhead_triggers_medium_priority_recommendation(self):
        features = _make_features(
            purchase_price=Decimal("100000.00"),
            total_expenses=Decimal("30000.00"),
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)

        recs = self.engine.get_sorted()
        expense_recs = [r for r in recs if r.rule_id == "property_high_expense_overhead"]
        self.assertEqual(len(expense_recs), 1)

        rec = expense_recs[0]
        self.assertEqual(rec.priority, RecommendationPriority.MEDIUM)
        self.assertEqual(rec.category, RecommendationCategory.FINANCE)
        self.assertEqual(rec.triggered_by_value, Decimal("30.00"))
        self.assertEqual(rec.threshold_value, HIGH_EXPENSE_RATIO_THRESHOLD)
        self.assertIn("/finances/properties/1/expenses/", rec.action_url)
        self.assertTrue(any("30.00%" in i for i in insights))

    def test_moderate_expense_overhead_does_not_trigger_recommendation(self):
        features = _make_features(
            purchase_price=Decimal("100000.00"),
            total_expenses=Decimal("10000.00"),
        )
        evaluate_property_rules(features, self.engine)
        recs = self.engine.get_sorted()
        expense_recs = [r for r in recs if r.rule_id == "property_high_expense_overhead"]
        self.assertEqual(expense_recs, [])

    # --- Target Selling Price Rules ---

    def test_target_selling_price_reached_triggers_opportunity_recommendation(self):
        features = _make_features(
            current_estimated_value=Decimal("150000.00"),
            expected_selling_price=Decimal("140000.00"),
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)

        recs = self.engine.get_sorted()
        target_recs = [r for r in recs if r.rule_id == "property_selling_target_met"]
        self.assertEqual(len(target_recs), 1)

        rec = target_recs[0]
        self.assertEqual(rec.priority, RecommendationPriority.LOW)
        self.assertEqual(rec.category, RecommendationCategory.GROWTH)
        self.assertEqual(rec.triggered_by_value, Decimal("150000.00"))
        self.assertEqual(rec.threshold_value, Decimal("140000.00"))
        self.assertTrue(any("target selling price" in i for i in insights))

    def test_target_selling_price_not_reached_does_not_trigger(self):
        features = _make_features(
            current_estimated_value=Decimal("120000.00"),
            expected_selling_price=Decimal("150000.00"),
        )
        evaluate_property_rules(features, self.engine)
        recs = self.engine.get_sorted()
        target_recs = [r for r in recs if r.rule_id == "property_selling_target_met"]
        self.assertEqual(target_recs, [])

    # --- Stalled Development Rules ---

    def test_stalled_development_triggers_low_priority_recommendation(self):
        features = _make_features(
            development_status="RAW",
            days_held=400,
            total_expenses=Decimal("5000.00"),
            total_interest_paid=Decimal("2000.00"),
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)

        recs = self.engine.get_sorted()
        stalled_recs = [r for r in recs if r.rule_id == "property_stalled_development"]
        self.assertEqual(len(stalled_recs), 1)

        rec = stalled_recs[0]
        self.assertEqual(rec.priority, RecommendationPriority.LOW)
        self.assertEqual(rec.category, RecommendationCategory.OPERATIONS)
        self.assertEqual(rec.triggered_by_value, Decimal("400"))
        self.assertEqual(rec.threshold_value, Decimal(str(EXTENDED_HOLDING_DAYS_THRESHOLD)))
        self.assertTrue(any("held undeveloped" in i for i in insights))

    def test_developed_status_with_long_holding_does_not_trigger_stalled_rule(self):
        features = _make_features(
            development_status="DEVELOPED",
            days_held=500,
        )
        evaluate_property_rules(features, self.engine)
        recs = self.engine.get_sorted()
        stalled_recs = [r for r in recs if r.rule_id == "property_stalled_development"]
        self.assertEqual(stalled_recs, [])


# ===========================================================================
# 2. Data Completeness & Insufficient Data Handling
# ===========================================================================


class PropertyDataCompletenessTests(PureTestCase):
    """Test handling of missing financial fields."""

    def setUp(self):
        self.engine = RecommendationEngine(business_id=10)

    def test_missing_both_purchase_and_current_value_returns_insufficient_data(self):
        features = _make_features(
            purchase_price=None,
            current_estimated_value=None,
            total_invested=None,
            current_roi_pct=None,
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)

        self.assertEqual(status, AnalysisStatus.INSUFFICIENT_DATA)
        self.assertTrue(any("lacks both purchase price and current estimated value" in i for i in insights))
        self.assertIn("limited due to missing financial baseline", summary)

        recs = self.engine.get_sorted()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].rule_id, "property_missing_financial_baseline")
        self.assertEqual(recs[0].priority, RecommendationPriority.MEDIUM)

    def test_missing_purchase_price_only_returns_ok_with_recommendation(self):
        features = _make_features(
            purchase_price=None,
            current_estimated_value=Decimal("150000.00"),
            total_invested=None,
            current_roi_pct=None,
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)

        self.assertEqual(status, AnalysisStatus.OK)
        self.assertTrue(any("Original purchase price is unrecorded" in i for i in insights))

        recs = self.engine.get_sorted()
        missing_recs = [r for r in recs if r.rule_id == "property_missing_purchase_price"]
        self.assertEqual(len(missing_recs), 1)
        self.assertEqual(missing_recs[0].priority, RecommendationPriority.LOW)

    def test_missing_current_value_only_returns_ok_with_recommendation(self):
        features = _make_features(
            purchase_price=Decimal("100000.00"),
            current_estimated_value=None,
            total_invested=Decimal("100000.00"),
            current_roi_pct=None,
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)

        self.assertEqual(status, AnalysisStatus.OK)
        self.assertTrue(any("Current estimated market value is missing" in i for i in insights))

        recs = self.engine.get_sorted()
        missing_recs = [r for r in recs if r.rule_id == "property_missing_valuation"]
        self.assertEqual(len(missing_recs), 1)
        self.assertEqual(missing_recs[0].priority, RecommendationPriority.LOW)


# ===========================================================================
# 3. Arithmetic Safety & Boundary Tests
# ===========================================================================


class PropertyRuleBoundaryAndEdgeCaseTests(PureTestCase):
    """Test safe arithmetic on zeros, negatives, and exact thresholds."""

    def setUp(self):
        self.engine = RecommendationEngine(business_id=10)

    def test_zero_purchase_price_does_not_raise_zero_division(self):
        features = _make_features(
            purchase_price=Decimal("0.00"),
            total_expenses=Decimal("5000.00"),
            current_estimated_value=Decimal("10000.00"),
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)
        self.assertEqual(status, AnalysisStatus.OK)

    def test_zero_current_value_does_not_raise_error(self):
        features = _make_features(
            purchase_price=Decimal("100000.00"),
            current_estimated_value=Decimal("0.00"),
            total_invested=Decimal("100000.00"),
            current_roi_pct=Decimal("-100.00"),
        )
        status, insights, summary = evaluate_property_rules(features, self.engine)
        self.assertEqual(status, AnalysisStatus.OK)
        recs = self.engine.get_sorted()
        self.assertTrue(any(r.rule_id == "property_severe_negative_roi" for r in recs))

    def test_exact_threshold_boundaries(self):
        # Exactly 80.00% LTV should trigger high LTV
        features = _make_features(
            current_estimated_value=Decimal("100000.00"),
            outstanding_loan_balance=Decimal("80000.00"),
            loan_to_value_ratio=Decimal("80.00"),
        )
        evaluate_property_rules(features, self.engine)
        recs = self.engine.get_sorted()
        self.assertTrue(any(r.rule_id == "property_high_ltv" for r in recs))

        # Exactly 100.00% LTV is high LTV (not underwater, which is > 100%)
        engine2 = RecommendationEngine(business_id=10)
        features2 = _make_features(
            current_estimated_value=Decimal("100000.00"),
            outstanding_loan_balance=Decimal("100000.00"),
            loan_to_value_ratio=Decimal("100.00"),
        )
        evaluate_property_rules(features2, engine2)
        recs2 = engine2.get_sorted()
        self.assertTrue(any(r.rule_id == "property_high_ltv" for r in recs2))
        self.assertFalse(any(r.rule_id == "property_ltv_underwater" for r in recs2))

        # Exactly 25.00% expense ratio should trigger
        engine3 = RecommendationEngine(business_id=10)
        features3 = _make_features(
            purchase_price=Decimal("100000.00"),
            total_expenses=Decimal("25000.00"),
        )
        evaluate_property_rules(features3, engine3)
        recs3 = engine3.get_sorted()
        self.assertTrue(any(r.rule_id == "property_high_expense_overhead" for r in recs3))

        # Exactly -15.00% ROI should trigger severe negative ROI
        engine4 = RecommendationEngine(business_id=10)
        features4 = _make_features(
            current_roi_pct=Decimal("-15.00"),
            current_estimated_value=Decimal("85000.00"),
            total_invested=Decimal("100000.00"),
        )
        evaluate_property_rules(features4, engine4)
        recs4 = engine4.get_sorted()
        self.assertTrue(any(r.rule_id == "property_severe_negative_roi" for r in recs4))

        # Exactly 365 days held should trigger stalled development
        engine5 = RecommendationEngine(business_id=10)
        features5 = _make_features(
            development_status="RAW",
            days_held=365,
        )
        evaluate_property_rules(features5, engine5)
        recs5 = engine5.get_sorted()
        self.assertTrue(any(r.rule_id == "property_stalled_development" for r in recs5))

    def test_priority_sorting_critical_before_high_before_medium(self):
        # Triggers underwater (CRITICAL), severe negative ROI (HIGH), and high expenses (MEDIUM)
        features = _make_features(
            purchase_price=Decimal("100000.00"),
            total_invested=Decimal("130000.00"),
            total_expenses=Decimal("30000.00"),
            current_estimated_value=Decimal("50000.00"),
            outstanding_loan_balance=Decimal("60000.00"),
            loan_to_value_ratio=Decimal("120.00"),
            current_roi_pct=Decimal("-61.54"),
        )
        evaluate_property_rules(features, self.engine)
        recs = self.engine.get_sorted()

        self.assertGreaterEqual(len(recs), 3)
        self.assertEqual(recs[0].priority, RecommendationPriority.CRITICAL)
        self.assertEqual(recs[1].priority, RecommendationPriority.HIGH)
        self.assertEqual(recs[2].priority, RecommendationPriority.MEDIUM)


# ===========================================================================
# 4. End-to-End Integration & Tenant Isolation (Database)
# ===========================================================================


class PropertyAnalysisPipelineIntegrationTests(TestCase):
    """End-to-end integration tests using analyse_property with ORM models."""

    def setUp(self):
        from apps.businesses.models import Business, BusinessUser, Property

        User = get_user_model()
        self.user = User.objects.create_user(
            username="prop-ai-user", email="prop-ai@example.com", password="StrongPass123!"
        )
        self.other_user = User.objects.create_user(
            username="prop-other-user", email="prop-other@example.com", password="StrongPass123!"
        )

        self.business = Business.objects.create(name="AI Realty", owner=self.user)
        BusinessUser.objects.create(
            business=self.business, user=self.user, role=BusinessUser.Role.OWNER
        )

        self.other_business = Business.objects.create(
            name="Comp Realty", owner=self.other_user
        )
        BusinessUser.objects.create(
            business=self.other_business, user=self.other_user, role=BusinessUser.Role.OWNER
        )

    def test_analyse_property_with_high_debt_generates_explainable_critical_result(self):
        from apps.ai_engine.services.property_analysis import analyse_property
        from apps.businesses.models import Property
        from apps.finances.models import PropertyLoan

        prop = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Debt Tower",
            purchase_price=Decimal("100000.00"),
            current_estimated_value=Decimal("80000.00"),
        )
        PropertyLoan.objects.create(
            business=self.business,
            property=prop,
            lender_name="National Bank",
            principal_amount=Decimal("90000.00"),
            interest_rate=Decimal("10.00"),
            loan_start_date=date.today() - timedelta(days=60),
            loan_term_months=120,
            emi_amount=Decimal("1200.00"),
            outstanding_balance=Decimal("89000.00"),
            is_active=True,
        )

        result = analyse_property(self.user, property_id=prop.pk)

        self.assertEqual(result.status, AnalysisStatus.OK)
        self.assertEqual(result.property_id, prop.pk)
        self.assertEqual(result.business_id, self.business.pk)
        self.assertIsNotNone(result.features)

        # 89000 debt / 80000 value = 111.25% LTV -> underwater
        self.assertGreater(result.features.loan_to_value_ratio, Decimal("100.00"))
        self.assertTrue(len(result.recommendations) > 0)

        # Top recommendation must be underwater loan
        top_rec = result.recommendations[0]
        self.assertEqual(top_rec.rule_id, "property_ltv_underwater")
        self.assertEqual(top_rec.priority, RecommendationPriority.CRITICAL)
        self.assertEqual(top_rec.triggered_by_value, result.features.loan_to_value_ratio)
        self.assertIn("/finances/properties/", top_rec.action_url)
        self.assertIn("Debt Tower", result.summary)

    def test_analyse_property_with_missing_baseline_returns_insufficient_data(self):
        from apps.ai_engine.services.property_analysis import analyse_property
        from apps.businesses.models import Property

        blank_prop = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Blank Plot",
            purchase_price=None,
            current_estimated_value=None,
        )

        result = analyse_property(self.user, property_id=blank_prop.pk)

        self.assertEqual(result.status, AnalysisStatus.INSUFFICIENT_DATA)
        self.assertEqual(len(result.recommendations), 1)
        self.assertEqual(result.recommendations[0].rule_id, "property_missing_financial_baseline")
        self.assertIn("limited due to missing financial baseline", result.summary)

    def test_analyse_property_with_healthy_metrics_returns_ok_with_no_risk_flags(self):
        from apps.ai_engine.services.property_analysis import analyse_property
        from apps.businesses.models import Property

        healthy_prop = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Solid Oak Estate",
            purchase_price=Decimal("200000.00"),
            current_estimated_value=Decimal("260000.00"),
        )

        result = analyse_property(self.user, property_id=healthy_prop.pk)

        self.assertEqual(result.status, AnalysisStatus.OK)
        self.assertEqual(result.recommendations, [])
        self.assertEqual(result.insights, [])
        self.assertIn("Solid Oak Estate", result.summary)
        self.assertIn("No critical risk flags or urgent actions identified", result.summary)

    def test_analyse_property_enforces_tenant_isolation(self):
        from apps.ai_engine.services.property_analysis import analyse_property
        from apps.businesses.models import Property

        comp_prop = Property.objects.create(
            business=self.other_business,
            owner=self.other_user,
            name="Competitor Tower",
            purchase_price=Decimal("500000.00"),
            current_estimated_value=Decimal("600000.00"),
        )

        # Attempt horizontal privilege escalation
        with self.assertRaises(Http404):
            analyse_property(self.user, property_id=comp_prop.pk)

    def test_analyse_property_rejects_unauthenticated_user(self):
        from apps.ai_engine.services.property_analysis import analyse_property
        from django.contrib.auth.models import AnonymousUser
        from apps.businesses.models import Property

        prop = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Public Check Plot",
        )

        with self.assertRaises(PermissionDenied):
            analyse_property(AnonymousUser(), property_id=prop.pk)
