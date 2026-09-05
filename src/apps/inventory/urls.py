from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("stock/", views.stock_overview, name="stock_overview"),
    path("transactions/", views.inventory_transaction_list, name="transaction_list"),
    path("products/<int:product_id>/adjust/", views.update_stock, name="update_stock"),
]
