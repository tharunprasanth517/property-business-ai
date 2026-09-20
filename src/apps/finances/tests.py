from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.businesses.models import Business, BusinessUser, Property
from apps.analytics.services.property_finance_service import get_property_financial_summary

from .models import (
    ExpenseCategory,
    LoanPayment,
    PropertyExpense,
    PropertyLoan,
    PropertyTransaction,
)


class PropertyFinanceWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="finance-owner",
            email="finance-owner@example.com",
            password="StrongPass123!",
        )
        self.other_user = user_model.objects.create_user(
            username="finance-other",
            email="finance-other@example.com",
            password="StrongPass123!",
        )
        self.business = Business.objects.create(name="Finance Holdings", owner=self.user)
        BusinessUser.objects.create(
            business=self.business,
            user=self.user,
            role=BusinessUser.Role.OWNER,
        )
        self.other_business = Business.objects.create(name="Other Holdings", owner=self.other_user)
        BusinessUser.objects.create(
            business=self.other_business,
            user=self.other_user,
            role=BusinessUser.Role.OWNER,
        )
        self.property = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Finance Property",
            purchase_price=Decimal("1000.00"),
            current_estimated_value=Decimal("1400.00"),
            expected_selling_price=Decimal("1600.00"),
        )
        self.other_property = Property.objects.create(
            business=self.other_business,
            owner=self.other_user,
            name="Other Property",
        )
        self.client.force_login(self.user)
        self.set_active_business(self.business)

    def set_active_business(self, business):
        session = self.client.session
        session["active_business_id"] = business.pk
        session.save()

    def test_property_expense_creation_assigns_current_tenant(self):
        category = ExpenseCategory.objects.create(business=self.business, name="Repairs")
        response = self.client.post(
            reverse("finances:property_expense_create", args=[self.property.pk]),
            {
                "category": category.pk,
                "title": "Fence repair",
                "amount": "100.00",
                "expense_date": "2026-09-01",
                "is_recurring": "",
                "recurrence_period": "NONE",
                "notes": "Boundary maintenance",
            },
        )

        self.assertRedirects(
            response,
            reverse("businesses:property_detail", args=[self.property.pk]),
        )
        expense = PropertyExpense.objects.get(title="Fence repair")
        self.assertEqual(expense.business, self.business)
        self.assertEqual(expense.property, self.property)
        self.assertEqual(expense.recorded_by, self.user)

    def test_property_transaction_creation_updates_property(self):
        response = self.client.post(
            reverse("finances:property_transaction_create", args=[self.property.pk]),
            {
                "transaction_type": "PURCHASE",
                "amount": "1200.00",
                "transaction_date": "2026-09-02",
                "counterparty_name": "Seller",
                "notes": "Closing payment",
            },
        )

        self.assertRedirects(
            response,
            reverse("businesses:property_detail", args=[self.property.pk]),
        )
        transaction = PropertyTransaction.objects.get(property=self.property)
        self.assertEqual(transaction.business, self.business)
        self.assertEqual(transaction.recorded_by, self.user)
        self.property.refresh_from_db()
        self.assertEqual(self.property.purchase_price, Decimal("1200.00"))
        self.assertEqual(self.property.purchase_date, date(2026, 9, 2))
        self.assertEqual(self.property.ownership_status, Property.OwnershipStatus.OWNED)

    def test_loan_payment_updates_relationship_and_balance(self):
        loan = PropertyLoan.objects.create(
            business=self.business,
            property=self.property,
            lender_name="Local Bank",
            principal_amount=Decimal("1000.00"),
            interest_rate=Decimal("8.50"),
            loan_start_date=date(2026, 1, 1),
            loan_term_months=12,
            emi_amount=Decimal("90.00"),
            outstanding_balance=Decimal("1000.00"),
        )

        response = self.client.post(
            reverse("finances:loan_payment_create", args=[loan.pk]),
            {
                "payment_date": "2026-09-03",
                "principal_paid": "200.00",
                "interest_paid": "50.00",
                "total_paid": "250.00",
                "notes": "September payment",
            },
        )

        self.assertRedirects(
            response,
            reverse("businesses:property_detail", args=[self.property.pk]),
        )
        payment = LoanPayment.objects.get(loan=loan)
        self.assertEqual(payment.business, self.business)
        self.assertEqual(payment.recorded_by, self.user)
        loan.refresh_from_db()
        self.assertEqual(loan.outstanding_balance, Decimal("800.00"))
        self.assertTrue(loan.is_active)

    def test_property_financial_summary_calculates_costs_and_returns(self):
        category = ExpenseCategory.objects.create(business=self.business, name="Repairs")
        PropertyExpense.objects.create(
            business=self.business,
            property=self.property,
            category=category,
            title="Fence repair",
            amount=Decimal("100.00"),
            expense_date=date(2026, 9, 1),
            recorded_by=self.user,
        )
        loan = PropertyLoan.objects.create(
            business=self.business,
            property=self.property,
            lender_name="Local Bank",
            principal_amount=Decimal("1000.00"),
            interest_rate=Decimal("8.50"),
            loan_start_date=date(2026, 1, 1),
            loan_term_months=12,
            emi_amount=Decimal("90.00"),
            outstanding_balance=Decimal("800.00"),
        )
        LoanPayment.objects.create(
            business=self.business,
            loan=loan,
            payment_date=date(2026, 9, 3),
            principal_paid=Decimal("200.00"),
            interest_paid=Decimal("50.00"),
            total_paid=Decimal("250.00"),
            recorded_by=self.user,
        )

        summary = get_property_financial_summary(self.property, self.business)

        self.assertEqual(summary["total_expenses"], Decimal("100.00"))
        self.assertEqual(summary["total_expenses_by_category"], {"Repairs": Decimal("100.00")})
        self.assertEqual(summary["total_loan_principal"], Decimal("1000.00"))
        self.assertEqual(summary["total_interest_paid"], Decimal("50.00"))
        self.assertEqual(summary["total_principal_paid"], Decimal("200.00"))
        self.assertEqual(summary["outstanding_loan_balance"], Decimal("800.00"))
        self.assertEqual(summary["total_invested"], Decimal("1150.00"))
        self.assertEqual(summary["current_pnl"], Decimal("250.00"))
        self.assertEqual(summary["current_roi_pct"], Decimal("21.74"))
        self.assertEqual(summary["potential_pnl"], Decimal("450.00"))

    def test_property_finance_views_reject_property_outside_active_business(self):
        BusinessUser.objects.create(
            business=self.other_business,
            user=self.user,
            role=BusinessUser.Role.MEMBER,
        )

        urls = (
            reverse("finances:property_expense_list", args=[self.other_property.pk]),
            reverse("finances:property_expense_create", args=[self.other_property.pk]),
            reverse("finances:property_transaction_list", args=[self.other_property.pk]),
            reverse("finances:property_transaction_create", args=[self.other_property.pk]),
            reverse("finances:property_loan_list", args=[self.other_property.pk]),
            reverse("finances:property_loan_create", args=[self.other_property.pk]),
        )

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_unauthorized_user_cannot_access_another_business_financial_records(self):
        expense = PropertyExpense.objects.create(
            business=self.other_business,
            property=self.other_property,
            title="Private expense",
            amount=Decimal("25.00"),
            expense_date=date(2026, 9, 1),
        )
        loan = PropertyLoan.objects.create(
            business=self.other_business,
            property=self.other_property,
            lender_name="Other Bank",
            principal_amount=Decimal("500.00"),
            interest_rate=Decimal("7.00"),
            loan_start_date=date(2026, 1, 1),
            loan_term_months=12,
            emi_amount=Decimal("45.00"),
            outstanding_balance=Decimal("500.00"),
        )

        urls = (
            reverse("finances:property_expense_list", args=[self.other_property.pk]),
            reverse("finances:property_expense_edit", args=[expense.pk]),
            reverse("finances:property_expense_delete", args=[expense.pk]),
            reverse("finances:property_transaction_list", args=[self.other_property.pk]),
            reverse("finances:property_loan_list", args=[self.other_property.pk]),
            reverse("finances:property_loan_edit", args=[loan.pk]),
            reverse("finances:loan_payment_create", args=[loan.pk]),
        )

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
