"""Views for business setup, membership management, and tenant-aware dashboards."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import BusinessForm, PropertyForm
from .models import Business, BusinessUser, Property

ACTIVE_BUSINESS_SESSION_KEY = "active_business_id"


def get_user_businesses(user):
    """Return only businesses the user belongs to or owns."""
    return Business.objects.filter(memberships__user=user).distinct()


def get_user_business(user, business_id):
    """Return a business the user can access, or raise 404."""
    return get_object_or_404(get_user_businesses(user), pk=business_id)


def get_active_business(request, user):
    """Return the currently selected active business for this user."""
    businesses = get_user_businesses(user)
    active_id = request.session.get(ACTIVE_BUSINESS_SESSION_KEY)

    if active_id and businesses.filter(pk=active_id).exists():
        return businesses.get(pk=active_id)

    if businesses.exists():
        active_business = businesses.first()
        request.session[ACTIVE_BUSINESS_SESSION_KEY] = active_business.pk
        return active_business

    return None


@login_required
def business_list(request):
    """List all businesses the current user can access."""
    businesses = get_user_businesses(request.user)
    active_business = get_active_business(request, request.user)

    return render(
        request,
        "businesses/business_list.html",
        {
            "businesses": businesses,
            "active_business": active_business,
        },
    )


@login_required
def dashboard(request):
    """Primary tenant-aware dashboard. Keeps the user inside a valid business scope."""
    active_business = get_active_business(request, request.user)
    businesses = get_user_businesses(request.user)

    if active_business is None:
        return render(
            request,
            "businesses/dashboard.html",
            {
                "businesses": businesses,
                "active_business": None,
                "properties": [],
            },
        )

    recent_properties = Property.objects.filter(business=active_business).select_related("owner")[:10]
    context = {
        "businesses": businesses,
        "active_business": active_business,
        "properties": recent_properties,
        "member_count": active_business.memberships.count(),
    }
    return render(request, "businesses/dashboard.html", context)


@login_required
def business_detail(request, business_id):
    """Business detail page for a user-scoped tenant."""
    business = get_user_business(request.user, business_id)
    request.session[ACTIVE_BUSINESS_SESSION_KEY] = business.pk

    properties = Property.objects.filter(business=business).select_related("owner")
    return render(
        request,
        "businesses/business_detail.html",
        {
            "business": business,
            "properties": properties,
            "member_count": business.memberships.count(),
        },
    )


@login_required
def business_create(request):
    """Create a new business and automatically enroll the owner as OWNER."""
    if request.method == "POST":
        form = BusinessForm(request.POST)
        if form.is_valid():
            business = form.save(commit=False)
            business.owner = request.user
            business.save()
            BusinessUser.objects.get_or_create(
                business=business,
                user=request.user,
                defaults={"role": BusinessUser.Role.OWNER},
            )
            request.session[ACTIVE_BUSINESS_SESSION_KEY] = business.pk
            messages.success(request, f"Business '{business.name}' created successfully.")
            return redirect("businesses:dashboard")
    else:
        form = BusinessForm()

    return render(request, "businesses/business_form.html", {"form": form, "title": "Create Business"})


@login_required
def switch_business(request, business_id):
    """Set the active business in the session for the current user."""
    business = get_user_business(request.user, business_id)
    request.session[ACTIVE_BUSINESS_SESSION_KEY] = business.pk
    messages.success(request, f"Active business switched to '{business.name}'.")
    return redirect("businesses:dashboard")


@login_required
def property_list(request):
    """List properties in the active business only."""
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before adding properties.")
        return redirect("businesses:create")

    properties = Property.objects.filter(business=business).select_related("owner")
    return render(
        request,
        "businesses/property_list.html",
        {"business": business, "properties": properties},
    )


@login_required
def personal_property_list(request):
    """List personal properties that are not attached to a business."""
    properties = Property.objects.filter(owner=request.user, business__isnull=True).select_related("owner")
    return render(request, "businesses/property_list.html", {"properties": properties, "business": None})


@login_required
def property_create(request):
    """Create a property within the active tenant business or as personal property."""
    if request.method == "POST":
        form = PropertyForm(request.POST, user=request.user)
        if form.is_valid():
            property_obj = form.save(commit=False)
            property_obj.owner = request.user
            property_obj.business = form.cleaned_data.get("business") or None
            property_obj.save()
            messages.success(request, f"Property '{property_obj.name}' saved.")
            return redirect("businesses:property_list")
    else:
        form = PropertyForm(user=request.user)
        active_business = get_active_business(request, request.user)
        if active_business is not None:
            form.fields["business"].initial = active_business

    return render(request, "businesses/property_form.html", {"form": form, "title": "Add Property"})


@login_required
def property_detail(request, property_id):
    """Detail view with tenant isolation. Business-scoped properties must belong to current user's chosen business."""
    property_obj = get_object_or_404(Property.objects.select_related("business", "owner"), pk=property_id)

    if property_obj.business is not None:
        if not get_user_businesses(request.user).filter(pk=property_obj.business_id).exists():
            raise PermissionDenied
    elif property_obj.owner_id != request.user.pk:
        raise PermissionDenied

    return render(request, "businesses/property_detail.html", {"property": property_obj})


@login_required
def property_edit(request, property_id):
    """Edit a property only when the current user has access to the business or owns it personally."""
    property_obj = get_object_or_404(Property.objects.select_related("business"), pk=property_id)

    if property_obj.business is not None and not get_user_businesses(request.user).filter(pk=property_obj.business_id).exists():
        raise PermissionDenied
    if property_obj.business is None and property_obj.owner_id != request.user.pk:
        raise PermissionDenied

    if request.method == "POST":
        form = PropertyForm(request.POST, instance=property_obj, user=request.user)
        if form.is_valid():
            updated_property = form.save(commit=False)
            updated_property.owner = request.user
            updated_property.business = form.cleaned_data.get("business") or None
            updated_property.save()
            messages.success(request, f"Property '{updated_property.name}' updated.")
            return redirect("businesses:property_detail", property_id=updated_property.pk)
    else:
        form = PropertyForm(instance=property_obj, user=request.user)

    return render(request, "businesses/property_form.html", {"form": form, "title": "Edit Property"})


@login_required
def property_delete(request, property_id):
    """Delete a property only when access is authorized and still within the tenant scope."""
    property_obj = get_object_or_404(Property.objects.select_related("business"), pk=property_id)

    if property_obj.business is not None and not get_user_businesses(request.user).filter(pk=property_obj.business_id).exists():
        raise PermissionDenied
    if property_obj.business is None and property_obj.owner_id != request.user.pk:
        raise PermissionDenied

    if request.method == "POST":
        property_name = property_obj.name
        property_obj.delete()
        messages.success(request, f"Property '{property_name}' deleted.")
        return redirect("businesses:property_list")

    return render(request, "businesses/property_confirm_delete.html", {"property": property_obj})


@login_required
def buy_property(request):
    """Placeholder for future property purchase flows. Keeps the business context stable."""
    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")
    messages.info(request, "Purchase flow will be added in a later phase.")
    return redirect("businesses:property_list")
