"""Admin registrations for the finances app."""

from django.contrib import admin

from .models import ExpenseCategory, LoanPayment, PropertyExpense, PropertyLoan, PropertyTransaction


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "created_at")
    list_filter = ("business",)
    search_fields = ("name", "business__name")


@admin.register(PropertyExpense)
class PropertyExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "amount", "expense_date", "property", "business", "is_recurring")
    list_filter = ("business", "is_recurring", "recurrence_period", "category")
    search_fields = ("title", "business__name", "property__name")
    date_hierarchy = "expense_date"


@admin.register(PropertyTransaction)
class PropertyTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_type", "property", "amount", "transaction_date", "counterparty_name", "business")
    list_filter = ("transaction_type", "business")
    search_fields = ("property__name", "counterparty_name", "business__name")
    date_hierarchy = "transaction_date"


@admin.register(PropertyLoan)
class PropertyLoanAdmin(admin.ModelAdmin):
    list_display = ("lender_name", "property", "principal_amount", "interest_rate", "emi_amount", "outstanding_balance", "is_active")
    list_filter = ("business", "is_active")
    search_fields = ("lender_name", "property__name", "business__name")


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ("loan", "payment_date", "principal_paid", "interest_paid", "total_paid")
    list_filter = ("business",)
    date_hierarchy = "payment_date"
