from django.contrib import admin

from .models import InventoryTransaction, StockLevel


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ("business", "product", "quantity", "last_updated_at")
    search_fields = ("product__name", "business__name")


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ("business", "product", "transaction_type", "quantity_change", "quantity_after", "performed_by", "created_at")
    list_filter = ("transaction_type", "business")
    search_fields = ("product__name", "notes", "reference_id")
