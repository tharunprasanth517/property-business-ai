"""
Admin configuration for the accounts application.

Registers the custom User model with Django Admin using
UserAdmin to preserve all built-in admin features (password
change, permissions, groups, etc.).
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Admin panel for the custom User model.

    Inherits all standard UserAdmin behaviour (list display,
    search, filters, password management) and adds the email
    field to the column list for convenience.
    """

    list_display = ("username", "email", "first_name", "last_name", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
