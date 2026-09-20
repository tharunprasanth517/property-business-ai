"""Forms for the finances app."""

from django import forms

from .models import ExpenseCategory, LoanPayment, PropertyExpense, PropertyLoan, PropertyTransaction


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ("name", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class PropertyExpenseForm(forms.ModelForm):
    class Meta:
        model = PropertyExpense
        fields = (
            "category",
            "title",
            "amount",
            "expense_date",
            "is_recurring",
            "recurrence_period",
            "notes",
        )
        widgets = {
            "expense_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, business, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ExpenseCategory.objects.filter(business=business)
        self.fields["category"].required = False


class PropertyTransactionForm(forms.ModelForm):
    class Meta:
        model = PropertyTransaction
        fields = (
            "transaction_type",
            "amount",
            "transaction_date",
            "counterparty_name",
            "notes",
        )
        widgets = {
            "transaction_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class PropertyLoanForm(forms.ModelForm):
    class Meta:
        model = PropertyLoan
        fields = (
            "lender_name",
            "principal_amount",
            "interest_rate",
            "loan_start_date",
            "loan_term_months",
            "emi_amount",
            "outstanding_balance",
            "notes",
        )
        widgets = {
            "loan_start_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class LoanPaymentForm(forms.ModelForm):
    class Meta:
        model = LoanPayment
        fields = (
            "payment_date",
            "principal_paid",
            "interest_paid",
            "total_paid",
            "notes",
        )
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
