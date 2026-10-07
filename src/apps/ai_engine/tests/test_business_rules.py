"""
Phase 6 Step 3 — Business intelligence rules and pipeline test suite.

Coverage:
  1. Unit tests for each deterministic rule in isolation using pure BusinessFeatures DTOs:
     - Severe net loss (net margin <= -20.00% -> CRITICAL)
     - Moderate net loss (net profit < 0, net margin > -20.00% -> HIGH)
     - Net loss without revenue (pure expense burden -> HIGH)
     - Profitable operations (no net loss alerts, positive insight)
     - Negative gross margin (gross margin < 0.00% -> CRITICAL)
     - Low gross margin (0.00% <= gross margin < 20.00% -> HIGH)
     - Healthy gross margin (>= 20.00% -> no low gross margin alert)
     - High operating expense burden (expense ratio >= 40.00% -> MEDIUM)
     - Safe operating expense burden (< 40.00% -> no alert)
     - High unallocated property overhead drag (overhead ratio >= 20.00% -> MEDIUM)
     - Safe unallocated property overhead drag (< 20.00% -> no alert)
     - Critical stock depletion by count (>= 5 low stock products -> HIGH)
     - Critical stock depletion by ratio (>= 50% of catalog low stock -> HIGH)
     - Moderate low stock depletion (< 5 and < 50% -> MEDIUM)
     - Zero low stock (no low stock alert)
     - Catalog active products with no sales recorded -> LOW
     - No catalog products and no sales -> no missing sales alert
     - High portfolio debt leverage (loans / portfolio value >= 80.00% -> HIGH)
     - Safe portfolio debt leverage (< 80.00% -> no leverage alert)
     - High debt-to-revenue exposure (loans >= 3x revenue -> MEDIUM)
     - Safe debt-to-revenue exposure (< 3x -> no alert)
  2. Data completeness & insufficient data handling:
     - Empty business (no properties, no products, no transactions) -> INSUFFICIENT_DATA status
     - Business with properties only -> OK status, 0 alerts
     - Business with products only -> OK status + record sales recommendation
  3. Safe arithmetic & edge cases:
     - Zero revenue, zero COGS, zero expenses
     - Boundary values (exact 20.00%, -20.00%, 40.00%, 80.00%, 3.00x)
     - None values in all optional fields
  4. Explainability & structure:
     - Recommendation fields: rule_id, triggered_by_value, threshold_value, action_url
     - Priority sort ordering (CRITICAL -> HIGH -> MEDIUM -> LOW)
     - Factual summary and insights correctness
  5. End-to-end integration & tenant isolation via analyse_business:
     - Full DB pipeline with sales, purchases, expenses, stock, and properties
     - Insufficient data DB record
     - Cross-tenant access rejection (Http404)
     - Unauthenticated access rejection (PermissionDenied)
     - User with no businesses rejection (PermissionDenied)
"""

from datetime import date
from decimal import Decimal
from unittest import TestCase as PureTestCase

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TestCase

from apps.ai_engine.services.contracts import (
    AnalysisStatus,
    BusinessFeatures,
    RecommendationCategory,
    RecommendationPriority,
)
from apps.ai_engine.services.business_rules import (
    CRITICAL_LOW_STOCK_COUNT_THRESHOLD,
    CRITICAL_LOW_STOCK_RATIO_THRESHOLD,
    HIGH_DEBT_TO_REVENUE_THRESHOLD,
    HIGH_EXPENSE_RATIO_THRESHOLD,
    HIGH_PORTFOLIO_LTV_THRESHOLD,
    HIGH_PROPERTY_OVERHEAD_THRESHOLD,
    LOW_GROSS_MARGIN_THRESHOLD,
    SEVERE_NET_LOSS_MARGIN_THRESHOLD,
    evaluate_business_rules,
)
from apps.ai_engine.services.recommendation_engine import RecommendationEngine


# ---------------------------------------------------------------------------
# Helper: create mock BusinessFeatures for pure unit tests
# ---------------------------------------------------------------------------


def _make_features(**kwargs) -> BusinessFeatures:
    defaults = {
        "business_id": 10,
        "business_name": "Apex Enterprises",
        "revenue": Decimal("100000.00"),
        "cogs": Decimal("60000.00"),
        "gross_profit": Decimal("40000.00"),
        "operating_expenses": Decimal("20000.00"),
        "property_overhead": Decimal("0.00"),
        "net_profit": Decimal("20000.00"),
        "gross_margin_pct": Decimal("40.00"),
        "net_margin_pct": Decimal("20.00"),
        "expense_ratio_pct": Decimal("20.00"),
        "property_count": 1,
        "total_portfolio_value": Decimal("500000.00"),
        "total_outstanding_loans": None,
        "product_count": 5,
        "low_stock_product_count": 0,
        "total_stock_value": Decimal("50000.00"),
        "transaction_days": 10,
    }
    defaults.update(kwargs)
    return BusinessFeatures(**defaults)


# ===========================================================================
# 1. Unit Tests: Pure Rule Evaluation (No DB)
# ===========================================================================


class BusinessRuleUnitTests(PureTestCase):
    """Test individual deterministic business rules in isolation."""

    def setUp(self):
        self.engine = RecommendationEngine(business_id=10)

    # --- Net Loss Rules ---

    def test_severe_net_loss_triggers_critical_recommendation(self):
        features = _make_features(
            revenue=Decimal("100000.00"),
            net_profit=Decimal("-25000.00"),
            net_margin_pct=Decimal("-25.00"),
        )
        status, insights, summary = evaluate_business_rules(features, self.engine)
        self.assertEqual(status, AnalysisStatus.OK)
        recs = self.engine.get_sorted()
        loss_recs = [r for r in recs if r.rule_id == "business_severe_net_loss"]
        self.assertEqual(len(loss_recs), 1)
        r = loss_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.CRITICAL)
        self.assertEqual(r.category, RecommendationCategory.FINANCE)
        self.assertEqual(r.triggered_by_value, Decimal("-25.00"))
        self.assertEqual(r.threshold_value, SEVERE_NET_LOSS_MARGIN_THRESHOLD)
        self.assertEqual(r.action_url, "/analytics/")
        self.assertTrue(any("severe net loss" in ins for ins in insights))

    def test_moderate_net_loss_triggers_high_recommendation(self):
        features = _make_features(
            revenue=Decimal("100000.00"),
            net_profit=Decimal("-10000.00"),
            net_margin_pct=Decimal("-10.00"),
        )
        status, insights, summary = evaluate_business_rules(features, self.engine)
        self.assertEqual(status, AnalysisStatus.OK)
        recs = self.engine.get_sorted()
        loss_recs = [r for r in recs if r.rule_id == "business_net_loss"]
        self.assertEqual(len(loss_recs), 1)
        r = loss_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.HIGH)
        self.assertEqual(r.category, RecommendationCategory.FINANCE)
        self.assertEqual(r.triggered_by_value, Decimal("-10000.00"))
        self.assertEqual(r.threshold_value, Decimal("0.00"))
        self.assertEqual(r.action_url, "/analytics/")

    def test_net_loss_without_revenue_triggers_high_recommendation(self):
        # Business with expenses but 0 revenue
        features = _make_features(
            revenue=None,
            net_profit=Decimal("-5000.00"),
            net_margin_pct=None,
            operating_expenses=Decimal("5000.00"),
            product_count=0,
        )
        status, insights, summary = evaluate_business_rules(features, self.engine)
        self.assertEqual(status, AnalysisStatus.OK)
        recs = self.engine.get_sorted()
        loss_recs = [r for r in recs if r.rule_id == "business_net_loss"]
        self.assertEqual(len(loss_recs), 1)
        self.assertEqual(loss_recs[0].priority, RecommendationPriority.HIGH)

    def test_profitable_operations_generates_positive_insight_and_no_loss_rule(self):
        features = _make_features(
            net_profit=Decimal("30000.00"),
            net_margin_pct=Decimal("30.00"),
        )
        status, insights, summary = evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        loss_recs = [r for r in recs if "net_loss" in r.rule_id]
        self.assertEqual(len(loss_recs), 0)
        self.assertTrue(any("Profitable operating performance" in ins for ins in insights))

    # --- Gross Margin Rules ---

    def test_negative_gross_margin_triggers_critical_recommendation(self):
        # COGS (110k) exceeds revenue (100k)
        features = _make_features(
            revenue=Decimal("100000.00"),
            cogs=Decimal("110000.00"),
            gross_profit=Decimal("-10000.00"),
            gross_margin_pct=Decimal("-10.00"),
            net_profit=Decimal("-30000.00"),
            net_margin_pct=Decimal("-30.00"),
        )
        status, insights, summary = evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        gm_recs = [r for r in recs if r.rule_id == "business_negative_gross_margin"]
        self.assertEqual(len(gm_recs), 1)
        r = gm_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.CRITICAL)
        self.assertEqual(r.category, RecommendationCategory.FINANCE)
        self.assertEqual(r.triggered_by_value, Decimal("-10.00"))
        self.assertEqual(r.threshold_value, Decimal("0.00"))
        self.assertEqual(r.action_url, "/transactions/purchases/")
        self.assertTrue(any("Direct procurement costs exceed sales revenue" in ins for ins in insights))

    def test_low_gross_margin_triggers_high_recommendation(self):
        # Gross margin at 15.00% (below 20.00% threshold)
        features = _make_features(
            revenue=Decimal("100000.00"),
            cogs=Decimal("85000.00"),
            gross_profit=Decimal("15000.00"),
            gross_margin_pct=Decimal("15.00"),
        )
        status, insights, summary = evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        gm_recs = [r for r in recs if r.rule_id == "business_low_gross_margin"]
        self.assertEqual(len(gm_recs), 1)
        r = gm_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.HIGH)
        self.assertEqual(r.triggered_by_value, Decimal("15.00"))
        self.assertEqual(r.threshold_value, LOW_GROSS_MARGIN_THRESHOLD)
        self.assertEqual(r.action_url, "/transactions/purchases/")

    def test_healthy_gross_margin_no_low_margin_recommendation(self):
        features = _make_features(gross_margin_pct=Decimal("35.00"))
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        self.assertFalse(any("gross_margin" in r.rule_id for r in recs))

    # --- Operating Expense Burden Rules ---

    def test_high_expense_burden_triggers_medium_recommendation(self):
        # Operating expenses consume 45.00% of revenue (threshold: 40.00%)
        features = _make_features(
            revenue=Decimal("100000.00"),
            operating_expenses=Decimal("45000.00"),
            expense_ratio_pct=Decimal("45.00"),
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        exp_recs = [r for r in recs if r.rule_id == "business_high_expense_burden"]
        self.assertEqual(len(exp_recs), 1)
        r = exp_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.MEDIUM)
        self.assertEqual(r.category, RecommendationCategory.FINANCE)
        self.assertEqual(r.triggered_by_value, Decimal("45.00"))
        self.assertEqual(r.threshold_value, HIGH_EXPENSE_RATIO_THRESHOLD)
        self.assertEqual(r.action_url, "/transactions/expenses/")

    def test_safe_expense_burden_no_recommendation(self):
        features = _make_features(
            revenue=Decimal("100000.00"),
            operating_expenses=Decimal("20000.00"),
            expense_ratio_pct=Decimal("20.00"),
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        self.assertFalse(any(r.rule_id == "business_high_expense_burden" for r in recs))

    # --- Property Overhead Drag Rules ---

    def test_high_property_overhead_triggers_medium_recommendation(self):
        # Overhead 25,000 on 100,000 revenue = 25.00% (threshold: 20.00%)
        features = _make_features(
            revenue=Decimal("100000.00"),
            property_overhead=Decimal("25000.00"),
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        ovh_recs = [r for r in recs if r.rule_id == "business_high_property_overhead"]
        self.assertEqual(len(ovh_recs), 1)
        r = ovh_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.MEDIUM)
        self.assertEqual(r.triggered_by_value, Decimal("25.00"))
        self.assertEqual(r.threshold_value, HIGH_PROPERTY_OVERHEAD_THRESHOLD)
        self.assertEqual(r.action_url, "/finances/categories/")

    def test_safe_property_overhead_no_recommendation(self):
        features = _make_features(
            revenue=Decimal("100000.00"),
            property_overhead=Decimal("5000.00"),
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        self.assertFalse(any(r.rule_id == "business_high_property_overhead" for r in recs))

    # --- Inventory & Stock Health Rules ---

    def test_critical_stock_depletion_by_count_triggers_high_recommendation(self):
        # 6 products low stock (>= 5) out of 20
        features = _make_features(
            product_count=20,
            low_stock_product_count=6,
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        stock_recs = [r for r in recs if r.rule_id == "business_critical_stock_depletion"]
        self.assertEqual(len(stock_recs), 1)
        r = stock_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.HIGH)
        self.assertEqual(r.category, RecommendationCategory.INVENTORY)
        self.assertEqual(r.action_url, "/inventory/stock/")

    def test_critical_stock_depletion_by_ratio_triggers_high_recommendation(self):
        # 2 products low stock out of 4 (50% >= 50%)
        features = _make_features(
            product_count=4,
            low_stock_product_count=2,
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        stock_recs = [r for r in recs if r.rule_id == "business_critical_stock_depletion"]
        self.assertEqual(len(stock_recs), 1)
        self.assertEqual(stock_recs[0].priority, RecommendationPriority.HIGH)

    def test_moderate_low_stock_triggers_medium_recommendation(self):
        # 2 products low stock out of 10 (< 5 and < 50%)
        features = _make_features(
            product_count=10,
            low_stock_product_count=2,
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        stock_recs = [r for r in recs if r.rule_id == "business_low_stock_risk"]
        self.assertEqual(len(stock_recs), 1)
        r = stock_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.MEDIUM)
        self.assertEqual(r.category, RecommendationCategory.INVENTORY)
        self.assertEqual(r.action_url, "/inventory/stock/")

    def test_zero_low_stock_no_stock_recommendation(self):
        features = _make_features(product_count=10, low_stock_product_count=0)
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        self.assertFalse(any(r.category == RecommendationCategory.INVENTORY for r in recs))

    # --- Missing Sales Activity Rules ---

    def test_active_products_with_no_sales_recorded_triggers_low_recommendation(self):
        features = _make_features(
            product_count=5,
            revenue=None,
            net_profit=None,
            gross_profit=None,
            gross_margin_pct=None,
            net_margin_pct=None,
            expense_ratio_pct=None,
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        sales_recs = [r for r in recs if r.rule_id == "business_no_sales_recorded"]
        self.assertEqual(len(sales_recs), 1)
        r = sales_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.LOW)
        self.assertEqual(r.category, RecommendationCategory.GROWTH)
        self.assertEqual(r.action_url, "/transactions/sales/add/")

    def test_zero_products_no_missing_sales_recommendation(self):
        features = _make_features(
            product_count=0,
            revenue=None,
            net_profit=None,
            gross_profit=None,
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        self.assertFalse(any(r.rule_id == "business_no_sales_recorded" for r in recs))

    # --- Debt & Portfolio Leverage Rules ---

    def test_high_portfolio_leverage_triggers_high_recommendation(self):
        # Loans 850,000 on portfolio value 1,000,000 = 85.00% (threshold: 80.00%)
        features = _make_features(
            total_portfolio_value=Decimal("1000000.00"),
            total_outstanding_loans=Decimal("850000.00"),
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        lev_recs = [r for r in recs if r.rule_id == "business_high_portfolio_leverage"]
        self.assertEqual(len(lev_recs), 1)
        r = lev_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.HIGH)
        self.assertEqual(r.category, RecommendationCategory.FINANCE)
        self.assertEqual(r.triggered_by_value, Decimal("85.00"))
        self.assertEqual(r.threshold_value, HIGH_PORTFOLIO_LTV_THRESHOLD)
        self.assertEqual(r.action_url, "/analytics/portfolio/")

    def test_safe_portfolio_leverage_no_recommendation(self):
        features = _make_features(
            total_portfolio_value=Decimal("1000000.00"),
            total_outstanding_loans=Decimal("400000.00"),
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        self.assertFalse(any(r.rule_id == "business_high_portfolio_leverage" for r in recs))

    def test_high_debt_to_revenue_triggers_medium_recommendation(self):
        # Loans 350,000 on revenue 100,000 = 3.50x (threshold: 3.00x)
        features = _make_features(
            revenue=Decimal("100000.00"),
            total_outstanding_loans=Decimal("350000.00"),
            total_portfolio_value=Decimal("1000000.00"),
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        dtr_recs = [r for r in recs if r.rule_id == "business_high_debt_to_revenue"]
        self.assertEqual(len(dtr_recs), 1)
        r = dtr_recs[0]
        self.assertEqual(r.priority, RecommendationPriority.MEDIUM)
        self.assertEqual(r.triggered_by_value, Decimal("3.50"))
        self.assertEqual(r.threshold_value, HIGH_DEBT_TO_REVENUE_THRESHOLD)
        self.assertEqual(r.action_url, "/analytics/")

    def test_safe_debt_to_revenue_no_recommendation(self):
        # Loans 150,000 on revenue 100,000 = 1.50x (< 3.00x)
        features = _make_features(
            revenue=Decimal("100000.00"),
            total_outstanding_loans=Decimal("150000.00"),
            total_portfolio_value=Decimal("1000000.00"),
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()
        self.assertFalse(any(r.rule_id == "business_high_debt_to_revenue" for r in recs))


# ===========================================================================
# 2. Data Completeness & Insufficient Data Handling
# ===========================================================================


class BusinessDataCompletenessTests(PureTestCase):
    """Verify behaviour with missing or empty business data."""

    def setUp(self):
        self.engine = RecommendationEngine(business_id=10)

    def test_completely_empty_business_returns_insufficient_data(self):
        empty_features = BusinessFeatures(
            business_id=10,
            business_name="Empty Startup Ltd",
            property_count=0,
            product_count=0,
            revenue=None,
            cogs=None,
            operating_expenses=None,
            property_overhead=None,
            total_outstanding_loans=None,
        )
        status, insights, summary = evaluate_business_rules(empty_features, self.engine)
        self.assertEqual(status, AnalysisStatus.INSUFFICIENT_DATA)
        self.assertTrue(any("no recorded properties" in ins for ins in insights))
        recs = self.engine.get_sorted()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].rule_id, "business_missing_operational_baseline")
        self.assertEqual(recs[0].priority, RecommendationPriority.MEDIUM)
        self.assertIn("limited due to a lack of recorded operational data", summary)

    def test_property_only_business_is_ok_status_with_no_false_warnings(self):
        # Property holding company without trading activity
        features = BusinessFeatures(
            business_id=10,
            business_name="Pure Property HoldCo",
            property_count=2,
            total_portfolio_value=Decimal("800000.00"),
            product_count=0,
            revenue=None,
            cogs=None,
            operating_expenses=None,
        )
        status, insights, summary = evaluate_business_rules(features, self.engine)
        self.assertEqual(status, AnalysisStatus.OK)
        recs = self.engine.get_sorted()
        self.assertEqual(recs, [])
        self.assertIn("Portfolio of 2 property assets", summary)
        self.assertIn("No critical risk flags or urgent actions identified", summary)


# ===========================================================================
# 3. Boundary & Decimal-Safety Tests
# ===========================================================================


class BusinessBoundaryAndSafetyTests(PureTestCase):
    """Test boundary conditions and arithmetic edge cases."""

    def setUp(self):
        self.engine = RecommendationEngine(business_id=10)

    def test_exact_boundary_gross_margin(self):
        # Exactly 20.00% is healthy, 19.99% is low
        features_exact = _make_features(gross_margin_pct=Decimal("20.00"))
        evaluate_business_rules(features_exact, self.engine)
        self.assertFalse(any(r.rule_id == "business_low_gross_margin" for r in self.engine.get_sorted()))

        self.engine.clear()
        features_below = _make_features(gross_margin_pct=Decimal("19.99"))
        evaluate_business_rules(features_below, self.engine)
        self.assertTrue(any(r.rule_id == "business_low_gross_margin" for r in self.engine.get_sorted()))

    def test_exact_boundary_severe_net_loss(self):
        # Exactly -20.00% is severe (CRITICAL), -19.99% is moderate (HIGH)
        features_exact = _make_features(
            net_profit=Decimal("-20000.00"),
            net_margin_pct=Decimal("-20.00"),
        )
        evaluate_business_rules(features_exact, self.engine)
        recs = self.engine.get_sorted()
        self.assertTrue(any(r.rule_id == "business_severe_net_loss" for r in recs))

        self.engine.clear()
        features_above = _make_features(
            net_profit=Decimal("-19990.00"),
            net_margin_pct=Decimal("-19.99"),
        )
        evaluate_business_rules(features_above, self.engine)
        recs = self.engine.get_sorted()
        self.assertTrue(any(r.rule_id == "business_net_loss" for r in recs))
        self.assertFalse(any(r.rule_id == "business_severe_net_loss" for r in recs))

    def test_exact_boundary_expense_ratio(self):
        # Exactly 40.00% triggers high expense burden, 39.99% does not
        features_exact = _make_features(expense_ratio_pct=Decimal("40.00"))
        evaluate_business_rules(features_exact, self.engine)
        self.assertTrue(any(r.rule_id == "business_high_expense_burden" for r in self.engine.get_sorted()))

        self.engine.clear()
        features_below = _make_features(expense_ratio_pct=Decimal("39.99"))
        evaluate_business_rules(features_below, self.engine)
        self.assertFalse(any(r.rule_id == "business_high_expense_burden" for r in self.engine.get_sorted()))

    def test_exact_boundary_portfolio_ltv(self):
        # Exactly 80.00% triggers leverage alert, 79.99% does not
        features_exact = _make_features(
            total_portfolio_value=Decimal("100000.00"),
            total_outstanding_loans=Decimal("80000.00"),
        )
        evaluate_business_rules(features_exact, self.engine)
        self.assertTrue(any(r.rule_id == "business_high_portfolio_leverage" for r in self.engine.get_sorted()))

        self.engine.clear()
        features_below = _make_features(
            total_portfolio_value=Decimal("100000.00"),
            total_outstanding_loans=Decimal("79990.00"),
        )
        evaluate_business_rules(features_below, self.engine)
        self.assertFalse(any(r.rule_id == "business_high_portfolio_leverage" for r in self.engine.get_sorted()))

    def test_exact_boundary_debt_to_revenue(self):
        # Exactly 3.00x triggers high debt to revenue
        features_exact = _make_features(
            revenue=Decimal("100000.00"),
            total_outstanding_loans=Decimal("300000.00"),
            total_portfolio_value=Decimal("1000000.00"),
        )
        evaluate_business_rules(features_exact, self.engine)
        self.assertTrue(any(r.rule_id == "business_high_debt_to_revenue" for r in self.engine.get_sorted()))

    def test_zero_revenue_and_zero_values_handled_safely(self):
        features = _make_features(
            revenue=Decimal("0.00"),
            cogs=Decimal("0.00"),
            gross_profit=Decimal("0.00"),
            operating_expenses=Decimal("0.00"),
            property_overhead=Decimal("0.00"),
            net_profit=Decimal("0.00"),
            gross_margin_pct=None,
            net_margin_pct=None,
            expense_ratio_pct=None,
            total_portfolio_value=Decimal("0.00"),
            total_outstanding_loans=Decimal("0.00"),
            product_count=0,
            property_count=1,
        )
        # Must not raise ZeroDivisionError
        status, insights, summary = evaluate_business_rules(features, self.engine)
        self.assertEqual(status, AnalysisStatus.OK)

    def test_priority_sorting_order(self):
        # Produce a mix of CRITICAL, HIGH, MEDIUM, and LOW recommendations
        features = _make_features(
            revenue=Decimal("100000.00"),
            cogs=Decimal("120000.00"),          # Negative gross margin -> CRITICAL
            gross_profit=Decimal("-20000.00"),
            gross_margin_pct=Decimal("-20.00"),
            operating_expenses=Decimal("45000.00"), # High expense ratio -> MEDIUM
            expense_ratio_pct=Decimal("45.00"),
            net_profit=Decimal("-65000.00"),
            net_margin_pct=Decimal("-65.00"),   # Severe net loss -> CRITICAL
            product_count=10,
            low_stock_product_count=6,          # Critical low stock -> HIGH
            total_portfolio_value=Decimal("500000.00"),
            total_outstanding_loans=Decimal("450000.00"), # LTV 90% -> HIGH
        )
        evaluate_business_rules(features, self.engine)
        recs = self.engine.get_sorted()

        # Check priorities are monotonically ordered: CRITICAL <= HIGH <= MEDIUM <= LOW
        priority_ranks = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
        }
        ranks = [priority_ranks[r.priority] for r in recs]
        self.assertEqual(ranks, sorted(ranks))


# ===========================================================================
# 4. End-to-End Integration Tests via analyse_business
# ===========================================================================


class BusinessAnalysisIntegrationTests(TestCase):
    """End-to-end integration tests using ORM fixtures and analyse_business."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="biz-analyzer",
            email="biz-analyzer@example.com",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            username="biz-intruder",
            email="biz-intruder@example.com",
            password="StrongPass123!",
        )

        from apps.businesses.models import Business, BusinessUser, Property
        from apps.products.models import Product, ProductCategory
        from apps.inventory.models import StockLevel
        from apps.transactions.models import Sale, Purchase, BusinessExpense
        from apps.finances.models import PropertyExpense, PropertyLoan

        self.business = Business.objects.create(name="Starlight Corp", owner=self.user)
        BusinessUser.objects.create(business=self.business, user=self.user, role=BusinessUser.Role.OWNER)

        self.other_business = Business.objects.create(name="Moonlight Corp", owner=self.other_user)
        BusinessUser.objects.create(business=self.other_business, user=self.other_user, role=BusinessUser.Role.OWNER)

        # Category and Products
        self.cat = ProductCategory.objects.create(business=self.business, name="Electronics")
        self.prod1 = Product.objects.create(
            business=self.business,
            category=self.cat,
            name="Smart Relay",
            sku="RELAY-01",
            cost_price=Decimal("150.00"),
            selling_price=Decimal("300.00"),
            reorder_level=10,
            created_by=self.user,
        )
        self.prod2 = Product.objects.create(
            business=self.business,
            category=self.cat,
            name="Power Hub",
            sku="HUB-01",
            cost_price=Decimal("500.00"),
            selling_price=Decimal("1000.00"),
            reorder_level=5,
            created_by=self.user,
        )

        # Stock Levels: prod1 is low stock (5 <= 10)
        StockLevel.objects.create(business=self.business, product=self.prod1, quantity=5)
        StockLevel.objects.create(business=self.business, product=self.prod2, quantity=20)

        # Sales & Purchases: Revenue = 10,000, Purchases = 8,500 (Gross margin: 15.00% -> low)
        Sale.objects.create(
            business=self.business,
            customer_name="Client Alpha",
            sale_date=date(2026, 1, 10),
            total_amount=Decimal("10000.00"),
            recorded_by=self.user,
        )
        Purchase.objects.create(
            business=self.business,
            supplier_name="Supplier Beta",
            purchase_date=date(2026, 1, 12),
            total_amount=Decimal("8500.00"),
            recorded_by=self.user,
        )

        # Expenses: 4,500 opex (45% of revenue -> high expense burden)
        BusinessExpense.objects.create(
            business=self.business,
            category="Utilities",
            title="Office Electric",
            amount=Decimal("4500.00"),
            expense_date=date(2026, 1, 15),
            recorded_by=self.user,
        )

        # Net Profit = 10,000 - 8,500 - 4,500 = -3,000 (Net margin: -30.00% -> severe net loss)

        # Property
        self.prop = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Starlight HQ",
            purchase_price=Decimal("500000.00"),
            current_estimated_value=Decimal("600000.00"),
        )

    def test_full_pipeline_analysis_detects_expected_signals(self):
        from apps.ai_engine.services.business_analysis import analyse_business

        result = analyse_business(self.user, business_id=self.business.pk)

        self.assertEqual(result.status, AnalysisStatus.OK)
        self.assertEqual(result.business_id, self.business.pk)
        self.assertIsNotNone(result.features)
        self.assertEqual(result.features.revenue, Decimal("1000000.00") / 100) # 10000.00
        self.assertEqual(result.features.net_profit, Decimal("-3000.00"))
        self.assertEqual(result.features.net_margin_pct, Decimal("-30.00"))
        self.assertEqual(result.features.low_stock_product_count, 1)

        # Recommendations should include:
        # 1. Severe net loss (CRITICAL)
        # 2. Low gross margin (HIGH) - 15% < 20%
        # 3. Critical/Low stock risk (HIGH - 1 of 2 is 50%)
        # 4. High operating expense burden (MEDIUM) - 45% >= 40%
        recs = result.recommendations
        rule_ids = {r.rule_id for r in recs}
        self.assertIn("business_severe_net_loss", rule_ids)
        self.assertIn("business_low_gross_margin", rule_ids)
        self.assertIn("business_high_expense_burden", rule_ids)
        self.assertIn("business_critical_stock_depletion", rule_ids)

        # First recommendation must be CRITICAL
        self.assertEqual(recs[0].priority, RecommendationPriority.CRITICAL)

        # Insights must be populated
        self.assertTrue(len(result.insights) >= 3)
        self.assertTrue(len(result.summary) > 0)

    def test_empty_business_returns_insufficient_data_status(self):
        from apps.businesses.models import Business, BusinessUser
        from apps.ai_engine.services.business_analysis import analyse_business

        empty_biz = Business.objects.create(name="Bare Shell Ltd", owner=self.user)
        BusinessUser.objects.create(business=empty_biz, user=self.user, role=BusinessUser.Role.OWNER)

        result = analyse_business(self.user, business_id=empty_biz.pk)
        self.assertEqual(result.status, AnalysisStatus.INSUFFICIENT_DATA)
        self.assertEqual(len(result.recommendations), 1)
        self.assertEqual(result.recommendations[0].rule_id, "business_missing_operational_baseline")

    def test_cross_tenant_business_analysis_raises_404(self):
        from apps.ai_engine.services.business_analysis import analyse_business

        # User tries to analyse other_business
        with self.assertRaises(Http404):
            analyse_business(self.user, business_id=self.other_business.pk)

    def test_unauthenticated_user_raises_permission_denied(self):
        from django.contrib.auth.models import AnonymousUser
        from apps.ai_engine.services.business_analysis import analyse_business

        with self.assertRaises(PermissionDenied):
            analyse_business(AnonymousUser(), business_id=self.business.pk)

    def test_user_without_businesses_raises_permission_denied(self):
        from django.contrib.auth import get_user_model
        from apps.ai_engine.services.business_analysis import analyse_business

        orphan_user = get_user_model().objects.create_user(
            username="orphan-user",
            email="orphan@example.com",
            password="StrongPass123!",
        )
        with self.assertRaises(PermissionDenied):
            analyse_business(orphan_user, business_id=None)
