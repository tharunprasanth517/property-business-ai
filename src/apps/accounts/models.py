"""
Custom User model for Property Business AI.

Extends Django's AbstractUser to allow future role-based expansions
without breaking the authentication system. Using a custom User model
from the start avoids painful migrations later.

Phase 1A: Email is the primary identifier for login.
           No Business model attached yet (Phase 2).
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model.

    Extends AbstractUser so we inherit all of Django's built-in
    authentication fields (username, password, email, is_staff, …)
    and can add project-specific fields in future phases.

    Phase 1A additions:
      - email is required and unique (used as the login identifier)

    Future phases will add:
      - role (owner / employee / admin)
      - linked Business FK
    """

    # Make email required and unique so it can serve as the login identifier.
    # Username is still kept for Django admin compatibility.
    email = models.EmailField(
        unique=True,
        verbose_name="email address",
        help_text="Required. A valid email address.",
    )

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.email
