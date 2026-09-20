"""
Financial models for Property Business AI.

Covers:
  - ExpenseCategory    : user-defined taxonomy per business
  - PropertyExpense    : any outgoing cost linked to a property (or the business itself)
  - PropertyTransaction: capital event ledger (property purchase / sale / valuation update)
  - PropertyLoan       : loan taken against a property (home loan, mortgage, etc.)
  - LoanPayment        : individual EMI or partial payment against a loan
"""

from django.conf import settings
from django.db import models

from apps.businesses.models import Business, Property


class ExpenseCategory(models.Model):
    """User-defined category for classifying property / business expenses."""

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="expense_categories",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "name"],
                name="unique_expense_category_per_business",
            )
        ]

    def __str__(self):
        return f"{self.business.name} / {self.name}"


class PropertyExpense(models.Model):
    """
    Records every outgoing payment related to a property or general business overhead.

    If `property` is None, the expense belongs to the business as a whole
    (e.g. shared office electricity, accountant fees).
    """

    class RecurrencePeriod(models.TextChoices):
        NONE = "NONE", "One-time"
        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        ANNUAL = "ANNUAL", "Annual"

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="property_expenses",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="expenses",
        null=True,
        blank=True,
        help_text="Leave blank for business-level expenses not tied to a specific property.",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    expense_date = models.DateField()
    is_recurring = models.BooleanField(default=False)
    recurrence_period = models.CharField(
        max_length=20,
        choices=RecurrencePeriod.choices,
        default=RecurrencePeriod.NONE,
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        prop = self.property.name if self.property else "Business-level"
        return f"{self.title} — ₹{self.amount} ({prop})"


class PropertyTransaction(models.Model):
    """
    Capital event ledger for properties — records the purchase, sale, or
    valuation update of a property.

    Intentionally separate from InventoryTransaction, which records stock movements.
    """

    class TransactionType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        SALE = "SALE", "Sale"
        VALUATION_UPDATE = "VALUATION_UPDATE", "Valuation Update"

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="property_transactions",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="capital_transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_date = models.DateField()
    counterparty_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of seller (for PURCHASE) or buyer (for SALE).",
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_property_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-transaction_date", "-created_at"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} — {self.property.name} — ₹{self.amount}"


class PropertyLoan(models.Model):
    """Home loan / mortgage tracker for a property."""

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="property_loans",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="loans",
    )
    lender_name = models.CharField(max_length=200)
    principal_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Original loan principal (₹).",
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Annual interest rate (%).",
    )
    loan_start_date = models.DateField()
    loan_term_months = models.PositiveIntegerField(help_text="Loan tenure in months.")
    emi_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Monthly EMI amount (₹).",
    )
    outstanding_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Current outstanding balance (₹) — updated on each payment.",
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-loan_start_date"]

    def __str__(self):
        return f"{self.lender_name} loan — {self.property.name} — ₹{self.principal_amount}"


class LoanPayment(models.Model):
    """Individual EMI or partial payment against a PropertyLoan."""

    loan = models.ForeignKey(
        PropertyLoan,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    # Denormalised for efficient tenant-scoped filtering without joining through loan
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="loan_payments",
    )
    payment_date = models.DateField()
    principal_paid = models.DecimalField(max_digits=15, decimal_places=2)
    interest_paid = models.DecimalField(max_digits=15, decimal_places=2)
    total_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Principal + interest paid in this instalment (₹).",
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_loan_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-created_at"]

    def __str__(self):
        return f"Payment ₹{self.total_paid} on {self.payment_date} — {self.loan}"
