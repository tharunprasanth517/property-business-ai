from django.urls import path

from . import views

app_name = "businesses"

urlpatterns = [
    path("", views.dashboard, name="list"),
    path("create/", views.business_create, name="create"),
    path("<int:business_id>/", views.business_detail, name="detail"),
    path("<int:business_id>/switch/", views.switch_business, name="switch"),
    path("properties/", views.property_list, name="property_list"),
    path("properties/personal/", views.personal_property_list, name="personal_property_list"),
    path("properties/add/", views.property_create, name="property_create"),
    path("properties/<int:property_id>/", views.property_detail, name="property_detail"),
    path("properties/<int:property_id>/edit/", views.property_edit, name="property_edit"),
    path("properties/<int:property_id>/delete/", views.property_delete, name="property_delete"),
    path("buy/", views.buy_property, name="buy_property"),
]