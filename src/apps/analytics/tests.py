from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.businesses.models import Business, BusinessUser, Property
from apps.finances.models import PropertyExpense, PropertyLoan
from apps.transactions.models import BusinessExpense, Purchase, Sale

from .services.business_finance_service import get_business_pl_summary
from .services.portfolio_service import get_portfolio_summary


class AnalyticsServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="analytics-owner",
            email="analytics-owner@example.com",
            password="StrongPass123!",
        )
        self.other_user = user_model.objects.create_user(
            username="analytics-other",
            email="analytics-other@example.com",
            password="StrongPass123!",
        )
        self.business = Business.objects.create(name="Analytics Holdings", owner=self.user)
        BusinessUser.objects.create(
            business=self.business,
            user=self.user,
            role=BusinessUser.Role.OWNER,
        )
        self.other_business = Business.objects.create(name="Other Analytics Holdings", owner=self.other_user)
        BusinessUser.objects.create(
            business=self.other_business,
            user=self.other_user,
            role=BusinessUser.Role.OWNER,
        )
        self.property = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Analytics Property",
            purchase_price=Decimal("1000.00"),
            current_estimated_value=Decimal("1500.00"),
            expected_selling_price=Decimal("1800.00"),
        )
        self.other_property = Property.objects.create(
            business=self.other_business,
            owner=self.other_user,
            name="Private Analytics Property",
            purchase_price=Decimal("9000.00"),
            current_estimated_value=Decimal("12000.00"),
        )

    def test_business_p_and_l_and_monthly_chart_data(self):
        Sale.objects.create(
            business=self.business,
            customer_name="Customer",
            sale_date=date(2026, 9, 10),
            total_amount=Decimal("1000.00"),
        )
        Purchase.objects.create(
            business=self.business,
            supplier_name="Supplier",
            purchase_date=date(2026, 9, 5),
            total_amount=Decimal("400.00"),
        )
        BusinessExpense.objects.create(
            business=self.business,
            category="Marketing",
            title="Campaign",
            amount=Decimal("100.00"),
            expense_date=date(2026, 9, 12),
        )
        PropertyExpense.objects.create(
            business=self.business,
            title="Business overhead",
            amount=Decimal("50.00"),
            expense_date=date(2026, 9, 15),
        )

        summary = get_business_pl_summary(self.business)

        self.assertEqual(summary["revenue"], Decimal("1000.00"))
        self.assertEqual(summary["cogs"], Decimal("400.00"))
        self.assertEqual(summary["gross_profit"], Decimal("600.00"))
        self.assertEqual(summary["operating_expenses"], Decimal("100.00"))
        self.assertEqual(summary["property_overhead"], Decimal("50.00"))
        self.assertEqual(summary["net_profit"], Decimal("450.00"))
        self.assertEqual(summary["chart_labels"], ["2026-09"])
        self.assertEqual(summary["chart_revenue"], [1000.0])
        self.assertEqual(summary["chart_expenses"], [500.0])

    def test_business_p_and_l_date_range_excludes_outside_records(self):
        Sale.objects.create(
            business=self.business,
            customer_name="In range",
            sale_date=date(2026, 9, 10),
            total_amount=Decimal("1000.00"),
        )
        Sale.objects.create(
            business=self.business,
            customer_name="Out of range",
            sale_date=date(2026, 8, 10),
            total_amount=Decimal("9000.00"),
        )

        summary = get_business_pl_summary(
            self.business,
            date_from=date(2026, 9, 1),
            date_to=date(2026, 9, 30),
        )

        self.assertEqual(summary["revenue"], Decimal("1000.00"))
        self.assertEqual(summary["date_from"], date(2026, 9, 1))
        self.assertEqual(summary["date_to"], date(2026, 9, 30))

    def test_portfolio_summary_aggregates_only_requested_business(self):
        PropertyExpense.objects.create(
            business=self.business,
            property=self.property,
            title="Survey",
            amount=Decimal("100.00"),
            expense_date=date(2026, 9, 1),
        )
        PropertyLoan.objects.create(
            business=self.business,
            property=self.property,
            lender_name="Local Bank",
            principal_amount=Decimal("500.00"),
            interest_rate=Decimal("8.00"),
            loan_start_date=date(2026, 1, 1),
            loan_term_months=12,
            emi_amount=Decimal("50.00"),
            outstanding_balance=Decimal("400.00"),
        )
        PropertyExpense.objects.create(
            business=self.other_business,
            property=self.other_property,
            title="Private survey",
            amount=Decimal("900.00"),
            expense_date=date(2026, 9, 1),
        )

        summary = get_portfolio_summary(self.business)

        self.assertEqual(summary["property_count"], 1)
        self.assertEqual(summary["total_purchase_cost"], Decimal("1000.00"))
        self.assertEqual(summary["total_estimated_value"], Decimal("1500.00"))
        self.assertEqual(summary["total_expenses"], Decimal("100.00"))
        self.assertEqual(summary["total_outstanding_loans"], Decimal("400.00"))
        self.assertEqual(summary["net_equity"], Decimal("0.00"))
        self.assertEqual(summary["current_portfolio_pnl"], Decimal("400.00"))
        self.assertEqual(summary["chart_labels"], ["Analytics Property"])
        self.assertEqual(summary["chart_invested"], [1100.0])
