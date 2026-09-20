"""Views for the finances app.

All views enforce tenant isolation:
  - Active business is resolved from session via get_active_business().
    - Property-based endpoints require the active business.
    - Direct-URL access to individual records checks the owning business.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.businesses.views import get_active_business

from .forms import (
    ExpenseCategoryForm,
    LoanPaymentForm,
    PropertyExpenseForm,
    PropertyLoanForm,
    PropertyTransactionForm,
)
from .models import ExpenseCategory, LoanPayment, PropertyExpense, PropertyLoan, PropertyTransaction


# ---------------------------------------------------------------------------
# Expense Categories
# ---------------------------------------------------------------------------


@login_required
def expense_category_list(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before managing expense categories.")
        return redirect("businesses:create")

    categories = ExpenseCategory.objects.filter(business=business)
    return render(
        request,
        "finances/expense_category_list.html",
        {"business": business, "categories": categories},
    )


@login_required
def expense_category_create(request):
    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    if request.method == "POST":
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.business = business
            cat.save()
            messages.success(request, f"Category '{cat.name}' created.")
            return redirect("finances:expense_category_list")
    else:
        form = ExpenseCategoryForm()

    return render(
        request,
        "finances/expense_category_form.html",
        {"form": form, "title": "Add Expense Category", "business": business},
    )


@login_required
def expense_category_edit(request, category_id):
    business = get_active_business(request, request.user)
    cat = get_object_or_404(ExpenseCategory, pk=category_id, business=business)

    if request.method == "POST":
        form = ExpenseCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{cat.name}' updated.")
            return redirect("finances:expense_category_list")
    else:
        form = ExpenseCategoryForm(instance=cat)

    return render(
        request,
        "finances/expense_category_form.html",
        {"form": form, "title": "Edit Expense Category", "business": business},
    )


@login_required
def expense_category_delete(request, category_id):
    business = get_active_business(request, request.user)
    cat = get_object_or_404(ExpenseCategory, pk=category_id, business=business)

    if request.method == "POST":
        cat.delete()
        messages.success(request, "Category deleted.")
        return redirect("finances:expense_category_list")

    return render(request, "finances/expense_category_confirm_delete.html", {"category": cat})


# ---------------------------------------------------------------------------
# Property Expenses
# ---------------------------------------------------------------------------


@login_required
def property_expense_list(request, property_id):
    """List all expenses for a specific property in the active business."""
    from apps.businesses.models import Property

    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    property_obj = get_object_or_404(
        Property,
        pk=property_id,
        business=business,
    )
    expenses = PropertyExpense.objects.filter(business=business, property=property_obj).select_related(
        "category"
    )
    total = sum(e.amount for e in expenses)
    return render(
        request,
        "finances/property_expense_list.html",
        {
            "business": business,
            "property": property_obj,
            "expenses": expenses,
            "total": total,
        },
    )


@login_required
def property_expense_create(request, property_id):
    from apps.businesses.models import Property

    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    property_obj = get_object_or_404(
        Property,
        pk=property_id,
        business=business,
    )

    if request.method == "POST":
        form = PropertyExpenseForm(request.POST, business=business)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.business = business
            expense.property = property_obj
            expense.recorded_by = request.user
            expense.save()
            messages.success(request, f"Expense '{expense.title}' recorded.")
            return redirect("businesses:property_detail", property_id=property_obj.pk)
    else:
        form = PropertyExpenseForm(business=business)

    return render(
        request,
        "finances/property_expense_form.html",
        {"form": form, "title": "Add Expense", "property": property_obj},
    )


@login_required
def property_expense_edit(request, expense_id):
    business = get_active_business(request, request.user)
    expense = get_object_or_404(PropertyExpense, pk=expense_id, business=business)

    if request.method == "POST":
        form = PropertyExpenseForm(request.POST, instance=expense, business=business)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated.")
            return redirect(
                "businesses:property_detail", property_id=expense.property.pk
            )
    else:
        form = PropertyExpenseForm(instance=expense, business=business)

    return render(
        request,
        "finances/property_expense_form.html",
        {"form": form, "title": "Edit Expense", "property": expense.property},
    )


@login_required
def property_expense_delete(request, expense_id):
    business = get_active_business(request, request.user)
    expense = get_object_or_404(PropertyExpense, pk=expense_id, business=business)

    if request.method == "POST":
        prop_id = expense.property.pk if expense.property else None
        expense.delete()
        messages.success(request, "Expense deleted.")
        if prop_id:
            return redirect("businesses:property_detail", property_id=prop_id)
        return redirect("businesses:list")

    return render(request, "finances/property_expense_confirm_delete.html", {"expense": expense})


# ---------------------------------------------------------------------------
# Property Transactions (capital events)
# ---------------------------------------------------------------------------


@login_required
def property_transaction_list(request, property_id):
    from apps.businesses.models import Property

    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    property_obj = get_object_or_404(
        Property,
        pk=property_id,
        business=business,
    )
    transactions = PropertyTransaction.objects.filter(business=business, property=property_obj)
    return render(
        request,
        "finances/property_transaction_list.html",
        {"business": business, "property": property_obj, "transactions": transactions},
    )


@login_required
def property_transaction_create(request, property_id):
    from apps.businesses.models import Property

    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    property_obj = get_object_or_404(
        Property,
        pk=property_id,
        business=business,
    )

    if request.method == "POST":
        form = PropertyTransactionForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                txn = form.save(commit=False)
                txn.business = business
                txn.property = property_obj
                txn.recorded_by = request.user
                txn.save()

                # Auto-update property fields based on transaction type
                if txn.transaction_type == PropertyTransaction.TransactionType.PURCHASE:
                    property_obj.purchase_price = txn.amount
                    property_obj.purchase_date = txn.transaction_date
                    property_obj.ownership_status = "OWNED"
                    property_obj.save(update_fields=["purchase_price", "purchase_date", "ownership_status"])
                elif txn.transaction_type == PropertyTransaction.TransactionType.SALE:
                    property_obj.expected_selling_price = txn.amount
                    property_obj.ownership_status = "UNDER_CONTRACT"
                    property_obj.save(update_fields=["expected_selling_price", "ownership_status"])
                elif txn.transaction_type == PropertyTransaction.TransactionType.VALUATION_UPDATE:
                    property_obj.current_estimated_value = txn.amount
                    property_obj.save(update_fields=["current_estimated_value"])

            messages.success(request, f"Transaction recorded: {txn.get_transaction_type_display()} ₹{txn.amount}.")
            return redirect("businesses:property_detail", property_id=property_obj.pk)
    else:
        form = PropertyTransactionForm()

    return render(
        request,
        "finances/property_transaction_form.html",
        {"form": form, "title": "Record Property Transaction", "property": property_obj},
    )


# ---------------------------------------------------------------------------
# Property Loans
# ---------------------------------------------------------------------------


@login_required
def property_loan_list(request, property_id):
    from apps.businesses.models import Property

    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    property_obj = get_object_or_404(
        Property,
        pk=property_id,
        business=business,
    )
    loans = PropertyLoan.objects.filter(business=business, property=property_obj)
    return render(
        request,
        "finances/property_loan_list.html",
        {"business": business, "property": property_obj, "loans": loans},
    )


@login_required
def property_loan_create(request, property_id):
    from apps.businesses.models import Property

    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    property_obj = get_object_or_404(
        Property,
        pk=property_id,
        business=business,
    )

    if request.method == "POST":
        form = PropertyLoanForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.business = business
            loan.property = property_obj
            loan.save()
            messages.success(request, f"Loan from '{loan.lender_name}' added.")
            return redirect("businesses:property_detail", property_id=property_obj.pk)
    else:
        form = PropertyLoanForm()

    return render(
        request,
        "finances/property_loan_form.html",
        {"form": form, "title": "Add Loan", "property": property_obj},
    )


@login_required
def property_loan_edit(request, loan_id):
    business = get_active_business(request, request.user)
    loan = get_object_or_404(PropertyLoan, pk=loan_id, business=business)

    if request.method == "POST":
        form = PropertyLoanForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            messages.success(request, "Loan updated.")
            return redirect("businesses:property_detail", property_id=loan.property.pk)
    else:
        form = PropertyLoanForm(instance=loan)

    return render(
        request,
        "finances/property_loan_form.html",
        {"form": form, "title": "Edit Loan", "property": loan.property},
    )


# ---------------------------------------------------------------------------
# Loan Payments (EMI)
# ---------------------------------------------------------------------------


@login_required
def loan_payment_create(request, loan_id):
    business = get_active_business(request, request.user)
    loan = get_object_or_404(PropertyLoan, pk=loan_id, business=business)

    if request.method == "POST":
        form = LoanPaymentForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                payment = form.save(commit=False)
                payment.loan = loan
                payment.business = business
                payment.recorded_by = request.user
                payment.save()

                # Decrement outstanding balance
                loan.outstanding_balance = max(
                    0, loan.outstanding_balance - payment.principal_paid
                )
                if loan.outstanding_balance == 0:
                    loan.is_active = False
                loan.save(update_fields=["outstanding_balance", "is_active"])

            messages.success(request, f"EMI payment of ₹{payment.total_paid} recorded.")
            return redirect("businesses:property_detail", property_id=loan.property.pk)
    else:
        form = LoanPaymentForm()

    return render(
        request,
        "finances/loan_payment_form.html",
        {"form": form, "loan": loan, "property": loan.property},
    )
