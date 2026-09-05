from django.contrib import admin

from .models import Business, BusinessUser, Property


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__username", "owner__email")


@admin.register(BusinessUser)
class BusinessUserAdmin(admin.ModelAdmin):
    list_display = ("business", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("business__name", "user__username", "user__email")


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "property_type", "owner", "business", "ownership_status")
    list_filter = ("property_type", "ownership_status", "development_status")
    search_fields = ("name", "address", "owner__username", "business__name")