"""Business, membership, and property models for the decision platform."""

from django.conf import settings
from django.db import models


class Business(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_businesses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.memberships.count()


class BusinessUser(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Administrator"
        MANAGER = "MANAGER", "Manager"
        MEMBER = "MEMBER", "Member"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["business__name", "user__username"]
        constraints = [
            models.UniqueConstraint(fields=["business", "user"], name="unique_business_user"),
        ]

    def __str__(self):
        return f"{self.user} - {self.business} ({self.get_role_display()})"

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def can_manage(self):
        return self.role in {self.Role.OWNER, self.Role.ADMIN, self.Role.MANAGER}


class Property(models.Model):
    class PropertyType(models.TextChoices):
        LAND = "LAND", "Land"
        RESIDENTIAL = "RESIDENTIAL", "Residential"
        COMMERCIAL = "COMMERCIAL", "Commercial"
        AGRICULTURAL = "AGRICULTURAL", "Agricultural"
        MIXED_USE = "MIXED_USE", "Mixed use"
        OTHER = "OTHER", "Other"

    class OwnershipStatus(models.TextChoices):
        OWNED = "OWNED", "Owned"
        CO_OWNED = "CO_OWNED", "Co-owned"
        LEASED = "LEASED", "Leased"
        UNDER_CONTRACT = "UNDER_CONTRACT", "Under contract"
        PROSPECTIVE = "PROSPECTIVE", "Prospective"

    class DevelopmentStatus(models.TextChoices):
        RAW = "RAW", "Raw / undeveloped"
        PLANNED = "PLANNED", "Planned"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DEVELOPED = "DEVELOPED", "Developed"
        ON_HOLD = "ON_HOLD", "On hold"

    name = models.CharField(max_length=200)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices, default=PropertyType.LAND)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="properties",
    )
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    area = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    area_unit = models.CharField(max_length=30, default="sq ft")
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    current_estimated_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    ownership_status = models.CharField(max_length=20, choices=OwnershipStatus.choices, default=OwnershipStatus.OWNED)
    intended_purpose = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    development_status = models.CharField(max_length=20, choices=DevelopmentStatus.choices, default=DevelopmentStatus.RAW)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "name"]

    def __str__(self):
        return self.name