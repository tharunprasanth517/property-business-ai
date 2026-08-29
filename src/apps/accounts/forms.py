"""
Forms for the accounts application.

Provides clean registration and login forms that integrate with
Django's built-in authentication infrastructure.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class RegistrationForm(UserCreationForm):
    """
    Registration form for new users.

    Extends Django's UserCreationForm to include email and provide
    helpful labels. Password hashing is handled by Django's auth
    framework automatically — plain-text passwords are never stored.
    """

    email = forms.EmailField(
        required=True,
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit: bool = True) -> "User":
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """
    Login form.

    Thin wrapper around Django's AuthenticationForm so we can attach
    custom widget attributes (autocomplete, autofocus) without touching
    the underlying authentication logic.
    """

    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
