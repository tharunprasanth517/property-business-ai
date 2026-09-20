"""
Transaction models for Property Business AI.

Covers goods/product-level financial movements:
  - Purchase / PurchaseItem : supplier purchase orders
  - Sale / SaleItem         : customer sales invoices
  - BusinessExpense         : operational overhead not tied to inventory

Note: Property capital events (buying/selling land or buildings) live in
apps.finances.PropertyTransaction, not here.
"""

from django.conf import settings
from django.db import models

from apps.businesses.models import Business
from apps.products.models import Product


class Purchase(models.Model):
    """Supplier purchase order — goods coming into the business."""

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    supplier_name = models.CharField(max_length=200)
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Invoice or purchase order number from supplier.",
    )
    purchase_date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_purchases",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchase_date", "-created_at"]

    def __str__(self):
        return f"Purchase from {self.supplier_name} on {self.purchase_date} — ₹{self.total_amount}"

    def recalculate_total(self):
        """Recompute total_amount from line items and save."""
        total = sum(item.line_total for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=["total_amount"])


class PurchaseItem(models.Model):
    """A single product line within a Purchase."""

    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="purchase_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["product__name"]

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} × {self.quantity} @ ₹{self.unit_cost}"


class Sale(models.Model):
    """Customer sales invoice — goods leaving the business."""

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="sales",
    )
    customer_name = models.CharField(max_length=200)
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Invoice or order reference number.",
    )
    sale_date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_sales",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sale_date", "-created_at"]

    def __str__(self):
        return f"Sale to {self.customer_name} on {self.sale_date} — ₹{self.total_amount}"

    def recalculate_total(self):
        """Recompute total_amount from line items and save."""
        total = sum(item.line_total for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=["total_amount"])


class SaleItem(models.Model):
    """A single product line within a Sale."""

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sale_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["product__name"]

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} × {self.quantity} @ ₹{self.unit_price}"


class BusinessExpense(models.Model):
    """
    Operational expense for the business — covers non-inventory overhead
    such as marketing, salaries, software subscriptions, etc.
    """

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="business_expenses",
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Marketing, Salary, Software, Utilities",
    )
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    expense_date = models.DateField()
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_business_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return f"{self.title} — ₹{self.amount} ({self.expense_date})"
