from django.urls import path

from . import views

app_name = "finances"

urlpatterns = [
    # Expense Categories
    path("categories/", views.expense_category_list, name="expense_category_list"),
    path("categories/add/", views.expense_category_create, name="expense_category_create"),
    path("categories/<int:category_id>/edit/", views.expense_category_edit, name="expense_category_edit"),
    path("categories/<int:category_id>/delete/", views.expense_category_delete, name="expense_category_delete"),

    # Property Expenses
    path("properties/<int:property_id>/expenses/", views.property_expense_list, name="property_expense_list"),
    path("properties/<int:property_id>/expenses/add/", views.property_expense_create, name="property_expense_create"),
    path("expenses/<int:expense_id>/edit/", views.property_expense_edit, name="property_expense_edit"),
    path("expenses/<int:expense_id>/delete/", views.property_expense_delete, name="property_expense_delete"),

    # Property Transactions (capital events)
    path("properties/<int:property_id>/transactions/", views.property_transaction_list, name="property_transaction_list"),
    path("properties/<int:property_id>/transactions/add/", views.property_transaction_create, name="property_transaction_create"),

    # Property Loans
    path("properties/<int:property_id>/loans/", views.property_loan_list, name="property_loan_list"),
    path("properties/<int:property_id>/loans/add/", views.property_loan_create, name="property_loan_create"),
    path("loans/<int:loan_id>/edit/", views.property_loan_edit, name="property_loan_edit"),

    # Loan Payments (EMI)
    path("loans/<int:loan_id>/payments/add/", views.loan_payment_create, name="loan_payment_create"),
]
