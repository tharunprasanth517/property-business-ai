"""
context.py — Tenant-safe data access helpers for the ai_engine layer.

These helpers are the ONLY entry points through which ai_engine services
obtain ORM objects.  They enforce tenant isolation at the boundary so that
individual analysis services never need to re-implement access checks.

Rules enforced here:
  1. Never trust a bare ``business_id`` or ``property_id`` integer.
     Always verify that the authenticated user is a member of the business
     before returning any data.
  2. Never duplicate authentication logic from the core apps.
     Tenant access is delegated to ``apps.businesses.views.get_user_businesses``
     and ``apps.businesses.views.get_user_business``.
  3. All returned objects are Django model instances (or None / raise) —
     never raw dicts or querysets that could be filtered further without
     a tenant check.
  4. Property access always verifies the property belongs to a business
     the user can access; the property_id alone is not sufficient.

Public API
----------
get_business_context(user, business_id=None) → BusinessContext
get_property_context(user, property_id)      → PropertyContext

Both raise PermissionDenied if the user cannot access the requested object.
They raise Http404 if the object does not exist (delegated to get_object_or_404).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404

# Reuse the existing tenant-aware business helpers — do NOT reimplement them.
# Note: ACTIVE_BUSINESS_SESSION_KEY is intentionally NOT imported here.
# Session-based active-business selection requires a request object and belongs
# in the view layer only.  The ai_engine context layer is request-agnostic.
from apps.businesses.views import (
    get_user_businesses,
    get_user_business,
)
from apps.businesses.models import Business, Property


# ---------------------------------------------------------------------------
# Context containers
# ---------------------------------------------------------------------------


@dataclass
class BusinessContext:
    """
    Verified, tenant-safe context for a single Business.

    Attributes
    ----------
    user        : The authenticated Django User object.
    business    : The Business ORM instance — confirmed to be accessible by user.
    business_id : Convenience shortcut (== business.pk).
    """

    user: object          # Django User (typing avoids a hard AUTH_USER_MODEL import)
    business: Business
    business_id: int


@dataclass
class PropertyContext:
    """
    Verified, tenant-safe context for a single Property.

    Attributes
    ----------
    user        : The authenticated Django User object.
    business    : The Business that owns this property.
    property    : The Property ORM instance.
    business_id : Convenience shortcut (== business.pk).
    property_id : Convenience shortcut (== property.pk).
    """

    user: object
    business: Business
    property: Property
    business_id: int
    property_id: int


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_business_context(user, business_id: Optional[int] = None) -> BusinessContext:
    """
    Return a verified BusinessContext for the given user.

    If ``business_id`` is provided the user must be a member of that business.
    If ``business_id`` is None the function returns the first accessible business
    (alphabetical order, same as the rest of the platform).

    Raises
    ------
    PermissionDenied
        If the user is not authenticated (is anonymous) or has no businesses.
    Http404
        If ``business_id`` is provided but no matching, accessible business exists.
    """
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied(
            "ai_engine.context: unauthenticated user cannot obtain business context."
        )

    if business_id is not None:
        # get_user_business already raises Http404 when the business is absent
        # or the user is not a member — no further check needed.
        business = get_user_business(user, business_id)
    else:
        businesses = get_user_businesses(user)
        if not businesses.exists():
            raise PermissionDenied(
                "ai_engine.context: user has no accessible businesses."
            )
        business = businesses.first()

    return BusinessContext(
        user=user,
        business=business,
        business_id=business.pk,
    )


def get_property_context(user, property_id: int) -> PropertyContext:
    """
    Return a verified PropertyContext for the given user and property ID.

    The property must belong to one of the user's accessible businesses.
    This prevents horizontal privilege escalation via a guessed property_id.

    Raises
    ------
    PermissionDenied
        If the user is not authenticated or has no accessible businesses.
    Http404
        If no matching property exists within the user's businesses.
    """
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied(
            "ai_engine.context: unauthenticated user cannot obtain property context."
        )

    accessible_businesses = get_user_businesses(user)
    if not accessible_businesses.exists():
        raise PermissionDenied(
            "ai_engine.context: user has no accessible businesses."
        )

    # The double-filter (pk + business__in) prevents any cross-tenant access.
    property_obj = get_object_or_404(
        Property.objects.select_related("business"),
        pk=property_id,
        business__in=accessible_businesses,
    )

    return PropertyContext(
        user=user,
        business=property_obj.business,
        property=property_obj,
        business_id=property_obj.business.pk,
        property_id=property_obj.pk,
    )
