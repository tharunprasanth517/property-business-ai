from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.business_dashboard, name="business_dashboard"),
    path("portfolio/", views.portfolio_summary, name="portfolio_summary"),
]
