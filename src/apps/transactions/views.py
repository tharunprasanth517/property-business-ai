"""Views for the transactions app.

Purchase and Sale creation automatically create InventoryTransaction ledger entries
to keep stock levels consistent with every financial event.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.businesses.views import get_active_business, get_user_businesses
from apps.inventory.models import InventoryTransaction, StockLevel

from .forms import BusinessExpenseForm, PurchaseForm, PurchaseItemForm, SaleForm, SaleItemForm
from .models import BusinessExpense, Purchase, PurchaseItem, Sale, SaleItem


# ---------------------------------------------------------------------------
# Purchases
# ---------------------------------------------------------------------------


@login_required
def purchase_list(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before recording purchases.")
        return redirect("businesses:create")

    purchases = Purchase.objects.filter(business=business).prefetch_related("items")
    return render(
        request,
        "transactions/purchase_list.html",
        {"business": business, "purchases": purchases},
    )


@login_required
def purchase_create(request):
    """
    Create a Purchase with a single inline line item.
    On save, triggers an InventoryTransaction(PURCHASE) to update stock.
    """
    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    if request.method == "POST":
        purchase_form = PurchaseForm(request.POST)
        item_form = PurchaseItemForm(request.POST, business=business)

        if purchase_form.is_valid() and item_form.is_valid():
            with db_transaction.atomic():
                purchase = purchase_form.save(commit=False)
                purchase.business = business
                purchase.recorded_by = request.user
                purchase.save()

                item = item_form.save(commit=False)
                item.purchase = purchase
                item.save()

                purchase.recalculate_total()

                # Create InventoryTransaction ledger entry
                product = item.product
                stock, _ = StockLevel.objects.get_or_create(
                    business=business, product=product
                )
                qty_before = stock.quantity
                stock.quantity += item.quantity
                stock.save()

                InventoryTransaction.objects.create(
                    business=business,
                    product=product,
                    transaction_type=InventoryTransaction.TransactionType.PURCHASE,
                    quantity_change=item.quantity,
                    quantity_before=qty_before,
                    quantity_after=stock.quantity,
                    reference_id=str(purchase.pk),
                    notes=f"Purchase #{purchase.pk} from {purchase.supplier_name}",
                    performed_by=request.user,
                )

            messages.success(
                request,
                f"Purchase from '{purchase.supplier_name}' recorded. Stock updated for {product.name}.",
            )
            return redirect("transactions:purchase_list")
    else:
        purchase_form = PurchaseForm()
        item_form = PurchaseItemForm(business=business)

    return render(
        request,
        "transactions/purchase_form.html",
        {
            "purchase_form": purchase_form,
            "item_form": item_form,
            "title": "Record Purchase",
            "business": business,
        },
    )


@login_required
def purchase_detail(request, purchase_id):
    business = get_active_business(request, request.user)
    purchase = get_object_or_404(Purchase, pk=purchase_id, business=business)
    return render(
        request,
        "transactions/purchase_detail.html",
        {"purchase": purchase, "business": business},
    )


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------


@login_required
def sale_list(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before recording sales.")
        return redirect("businesses:create")

    sales = Sale.objects.filter(business=business).prefetch_related("items")
    return render(
        request,
        "transactions/sale_list.html",
        {"business": business, "sales": sales},
    )


@login_required
def sale_create(request):
    """
    Create a Sale with a single inline line item.
    On save, triggers an InventoryTransaction(SALE) to decrease stock.
    """
    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    if request.method == "POST":
        sale_form = SaleForm(request.POST)
        item_form = SaleItemForm(request.POST, business=business)

        if sale_form.is_valid() and item_form.is_valid():
            with db_transaction.atomic():
                sale = sale_form.save(commit=False)
                sale.business = business
                sale.recorded_by = request.user
                sale.save()

                item = item_form.save(commit=False)
                item.sale = sale
                item.save()

                sale.recalculate_total()

                # Create InventoryTransaction ledger entry
                product = item.product
                stock, _ = StockLevel.objects.get_or_create(
                    business=business, product=product
                )
                qty_before = stock.quantity
                stock.quantity = max(0, stock.quantity - item.quantity)
                stock.save()

                InventoryTransaction.objects.create(
                    business=business,
                    product=product,
                    transaction_type=InventoryTransaction.TransactionType.SALE,
                    quantity_change=-item.quantity,
                    quantity_before=qty_before,
                    quantity_after=stock.quantity,
                    reference_id=str(sale.pk),
                    notes=f"Sale #{sale.pk} to {sale.customer_name}",
                    performed_by=request.user,
                )

            messages.success(
                request,
                f"Sale to '{sale.customer_name}' recorded. Stock updated for {product.name}.",
            )
            return redirect("transactions:sale_list")
    else:
        sale_form = SaleForm()
        item_form = SaleItemForm(business=business)

    return render(
        request,
        "transactions/sale_form.html",
        {
            "sale_form": sale_form,
            "item_form": item_form,
            "title": "Record Sale",
            "business": business,
        },
    )


@login_required
def sale_detail(request, sale_id):
    business = get_active_business(request, request.user)
    sale = get_object_or_404(Sale, pk=sale_id, business=business)
    return render(
        request,
        "transactions/sale_detail.html",
        {"sale": sale, "business": business},
    )


# ---------------------------------------------------------------------------
# Business Expenses
# ---------------------------------------------------------------------------


@login_required
def business_expense_list(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before recording expenses.")
        return redirect("businesses:create")

    expenses = BusinessExpense.objects.filter(business=business)
    total = sum(e.amount for e in expenses)
    return render(
        request,
        "transactions/expense_list.html",
        {"business": business, "expenses": expenses, "total": total},
    )


@login_required
def business_expense_create(request):
    business = get_active_business(request, request.user)
    if business is None:
        return redirect("businesses:create")

    if request.method == "POST":
        form = BusinessExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.business = business
            expense.recorded_by = request.user
            expense.save()
            messages.success(request, f"Expense '{expense.title}' recorded.")
            return redirect("transactions:expense_list")
    else:
        form = BusinessExpenseForm()

    return render(
        request,
        "transactions/expense_form.html",
        {"form": form, "title": "Add Business Expense", "business": business},
    )


@login_required
def business_expense_edit(request, expense_id):
    business = get_active_business(request, request.user)
    expense = get_object_or_404(BusinessExpense, pk=expense_id, business=business)

    if request.method == "POST":
        form = BusinessExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated.")
            return redirect("transactions:expense_list")
    else:
        form = BusinessExpenseForm(instance=expense)

    return render(
        request,
        "transactions/expense_form.html",
        {"form": form, "title": "Edit Expense", "business": business},
    )


@login_required
def business_expense_delete(request, expense_id):
    business = get_active_business(request, request.user)
    expense = get_object_or_404(BusinessExpense, pk=expense_id, business=business)

    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")
        return redirect("transactions:expense_list")

    return render(
        request,
        "transactions/expense_confirm_delete.html",
        {"expense": expense, "business": business},
    )
