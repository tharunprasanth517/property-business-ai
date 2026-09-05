"""
Views for the accounts application.

Implements:
  - register   — new user sign-up (GET + POST)
  - login_view — session-based login (GET + POST)
  - logout_view — session destruction (POST)
  - dashboard  — temporary authenticated landing page

All views use Django's built-in authentication utilities.
No plain-text passwords are ever handled here; Django's auth
framework manages hashing transparently.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import LoginForm, RegistrationForm


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(request):
    """
    Handle new user registration.

    GET  — render the registration form.
    POST — validate, save the new user (with hashed password), then
           automatically log them in and redirect to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the new user in immediately after registration.
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect("accounts:dashboard")
        # Form is invalid — fall through to re-render with errors.
        messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------


def login_view(request):
    """
    Handle session-based login.

    GET  — render the login form.
    POST — authenticate credentials; on success create a session and
           redirect to next (or dashboard); on failure show an error.

    Django's ``authenticate()`` verifies the hashed password stored in
    the database — plain-text passwords are never compared directly.
    """
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            # Honour the ?next= redirect parameter if present.
            next_url = request.GET.get("next") or "accounts:dashboard"
            return redirect(next_url)
        messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm(request)

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """
    Destroy the current session and redirect to the login page.

    Only POST is accepted to protect against CSRF-based forced logouts.
    """
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("accounts:login")


# ---------------------------------------------------------------------------
# Temporary authenticated dashboard (Phase 1A placeholder)
# ---------------------------------------------------------------------------


@login_required
def dashboard(request):
    """
    Temporary landing page for authenticated users.

    This is a Phase 1A placeholder. It will be replaced by the full
    analytics dashboard in a later phase.
    """
    return redirect("businesses:list")
