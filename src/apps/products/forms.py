from django import forms

from .models import Product, ProductCategory


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ("name", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "category",
            "name",
            "sku",
            "description",
            "unit_of_measure",
            "cost_price",
            "selling_price",
            "reorder_level",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "cost_price": forms.NumberInput(attrs={"step": "0.01"}),
            "selling_price": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.business = business
        if business is not None:
            self.fields["category"].queryset = ProductCategory.objects.filter(business=business)
            self.fields["category"].empty_label = "General / uncategorized"

    def clean_sku(self):
        sku = (self.cleaned_data.get("sku") or "").strip()
        if not sku:
            return ""

        existing = Product.objects.filter(business=self.business, sku=sku)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError("A product with this SKU already exists in this business.")

        return sku
