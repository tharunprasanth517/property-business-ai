from django.urls import path

from . import views

app_name = "transactions"

urlpatterns = [
    # Purchases
    path("purchases/", views.purchase_list, name="purchase_list"),
    path("purchases/add/", views.purchase_create, name="purchase_create"),
    path("purchases/<int:purchase_id>/", views.purchase_detail, name="purchase_detail"),

    # Sales
    path("sales/", views.sale_list, name="sale_list"),
    path("sales/add/", views.sale_create, name="sale_create"),
    path("sales/<int:sale_id>/", views.sale_detail, name="sale_detail"),

    # Business Expenses
    path("expenses/", views.business_expense_list, name="expense_list"),
    path("expenses/add/", views.business_expense_create, name="expense_create"),
    path("expenses/<int:expense_id>/edit/", views.business_expense_edit, name="expense_edit"),
    path("expenses/<int:expense_id>/delete/", views.business_expense_delete, name="expense_delete"),
]
