from django.contrib import admin

from .models import Product, ProductCategory


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("business", "name", "description")
    search_fields = ("name", "business__name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("business", "name", "sku", "category", "selling_price", "reorder_level", "is_active")
    list_filter = ("business", "is_active", "category")
    search_fields = ("name", "sku", "business__name")
