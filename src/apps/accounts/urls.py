"""
URL configuration for the accounts application.

Namespace: accounts

Routes
------
accounts/register/  — new user registration
accounts/login/     — session login
accounts/logout/    — session logout (POST only)
accounts/dashboard/ — temporary authenticated home page (Phase 1A)
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
