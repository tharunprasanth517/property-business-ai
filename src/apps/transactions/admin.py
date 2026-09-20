"""Admin registrations for the transactions app."""

from django.contrib import admin

from .models import BusinessExpense, Purchase, PurchaseItem, Sale, SaleItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    readonly_fields = ("line_total",)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("line_total",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("supplier_name", "purchase_date", "total_amount", "business", "reference_number")
    list_filter = ("business",)
    search_fields = ("supplier_name", "reference_number", "business__name")
    date_hierarchy = "purchase_date"
    inlines = [PurchaseItemInline]


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "sale_date", "total_amount", "business", "reference_number")
    list_filter = ("business",)
    search_fields = ("customer_name", "reference_number", "business__name")
    date_hierarchy = "sale_date"
    inlines = [SaleItemInline]


@admin.register(BusinessExpense)
class BusinessExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "amount", "expense_date", "category", "business")
    list_filter = ("business", "category")
    search_fields = ("title", "category", "business__name")
    date_hierarchy = "expense_date"
