"""Forms for the transactions app."""

from django import forms

from .models import BusinessExpense, Purchase, PurchaseItem, Sale, SaleItem


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ("supplier_name", "reference_number", "purchase_date", "notes")
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ("product", "quantity", "unit_cost")

    def __init__(self, *args, business, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.products.models import Product
        self.fields["product"].queryset = Product.objects.filter(
            business=business, is_active=True
        )


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ("customer_name", "reference_number", "sale_date", "notes")
        widgets = {
            "sale_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ("product", "quantity", "unit_price")

    def __init__(self, *args, business, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.products.models import Product
        self.fields["product"].queryset = Product.objects.filter(
            business=business, is_active=True
        )


class BusinessExpenseForm(forms.ModelForm):
    class Meta:
        model = BusinessExpense
        fields = ("category", "title", "amount", "expense_date", "notes")
        widgets = {
            "expense_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
