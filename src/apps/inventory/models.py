from django.conf import settings
from django.db import models

from apps.businesses.models import Business
from apps.products.models import Product


class StockLevel(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="stock_levels")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_levels")
    quantity = models.IntegerField(default=0)
    last_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__name"]
        constraints = [
            models.UniqueConstraint(fields=["business", "product"], name="unique_business_product_stock"),
        ]

    def __str__(self):
        return f"{self.product.name}: {self.quantity} {self.product.unit_of_measure}"


class InventoryTransaction(models.Model):
    class TransactionType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        SALE = "SALE", "Sale"
        RETURN_IN = "RETURN_IN", "Return In"
        RETURN_OUT = "RETURN_OUT", "Return Out"
        DAMAGE = "DAMAGE", "Damage"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="inventory_transactions")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="inventory_transactions")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    quantity_change = models.IntegerField(help_text="Positive for stock in, negative for stock out")
    quantity_before = models.IntegerField(default=0)
    quantity_after = models.IntegerField(default=0)
    reference_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_transactions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} {self.transaction_type} ({self.quantity_change})"
