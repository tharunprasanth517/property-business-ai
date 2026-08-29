"""
AppConfig for the accounts application.

This configures the app label and sets the default auto field.
The app handles user registration, login, logout, and session management
using Django's built-in authentication framework.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"
