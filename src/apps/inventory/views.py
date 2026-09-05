from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.businesses.views import get_active_business
from apps.inventory.models import InventoryTransaction, StockLevel
from apps.products.models import Product


@login_required
def stock_overview(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before checking stock.")
        return redirect("businesses:create")

    stock_levels = StockLevel.objects.filter(business=business).select_related("product")
    low_stock = [item for item in stock_levels if item.product.reorder_level and item.quantity <= item.product.reorder_level]
    return render(request, "inventory/stock_overview.html", {"business": business, "stock_levels": stock_levels, "low_stock": low_stock})


@login_required
def inventory_transaction_list(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before viewing inventory movements.")
        return redirect("businesses:create")

    transactions = InventoryTransaction.objects.filter(business=business).select_related("product", "performed_by")[:50]
    return render(request, "inventory/transaction_list.html", {"business": business, "transactions": transactions})


@login_required
def update_stock(request, product_id):
    business = get_active_business(request, request.user)
    product = get_object_or_404(Product, pk=product_id, business=business)
    stock, _ = StockLevel.objects.get_or_create(business=business, product=product)

    if request.method == "POST":
        quantity_change = int(request.POST.get("quantity_change", 0))
        if quantity_change == 0:
            messages.warning(request, "No stock change provided.")
            return redirect("inventory:stock_overview")

        before = stock.quantity
        stock.quantity += quantity_change
        stock.quantity = max(stock.quantity, 0)
        stock.save()

        InventoryTransaction.objects.create(
            business=business,
            product=product,
            transaction_type=request.POST.get("transaction_type", InventoryTransaction.TransactionType.ADJUSTMENT),
            quantity_change=quantity_change,
            quantity_before=before,
            quantity_after=stock.quantity,
            performed_by=request.user,
            notes=request.POST.get("notes", ""),
        )
        messages.success(request, f"Stock updated for '{product.name}'.")
        return redirect("inventory:stock_overview")

    return render(request, "inventory/stock_adjustment_form.html", {"business": business, "product": product, "stock": stock})
