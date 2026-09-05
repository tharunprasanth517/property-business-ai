from django.conf import settings
from django.db import models

from apps.businesses.models import Business


class ProductCategory(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="product_categories")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["business", "name"], name="unique_business_product_category"),
        ]

    def __str__(self):
        return f"{self.business.name} / {self.name}"


class Product(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    unit_of_measure = models.CharField(max_length=50, default="unit")
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reorder_level = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_products")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["business", "sku"], name="unique_business_product_sku"),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku or 'No SKU'})"

    @property
    def current_stock(self):
        from apps.inventory.models import StockLevel

        stock, _ = StockLevel.objects.get_or_create(product=self, business=self.business)
        return stock.quantity

    @property
    def is_low_stock(self):
        return self.current_stock <= self.reorder_level
