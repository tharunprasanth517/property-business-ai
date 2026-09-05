from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("categories/", views.product_category_list, name="category_list"),
    path("categories/add/", views.product_category_create, name="category_create"),
    path("", views.product_list, name="product_list"),
    path("add/", views.product_create, name="product_create"),
    path("<int:product_id>/", views.product_detail, name="product_detail"),
    path("<int:product_id>/edit/", views.product_edit, name="product_edit"),
]
