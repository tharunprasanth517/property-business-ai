"""Forms for business and property management."""

from django import forms

from .models import Business, Property


class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ("name", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = (
            "business",
            "name",
            "address",
            "area",
            "property_type",
            "ownership_status",
            "purchase_price",
            "current_estimated_value",
            "expected_selling_price",
            "purchase_date",
            "notes",
        )
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["business"].queryset = Business.objects.filter(
            memberships__user=user
        ).distinct()
        self.fields["business"].required = True