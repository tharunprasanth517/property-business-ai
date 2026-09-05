from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.businesses.views import get_active_business, get_user_businesses
from .forms import ProductCategoryForm, ProductForm
from .models import Product, ProductCategory


@login_required
def product_category_list(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before managing products.")
        return redirect("businesses:create")

    categories = ProductCategory.objects.filter(business=business)
    return render(request, "products/category_list.html", {"business": business, "categories": categories})


@login_required
def product_category_create(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before managing products.")
        return redirect("businesses:create")

    if request.method == "POST":
        form = ProductCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.business = business
            category.save()
            messages.success(request, f"Category '{category.name}' created.")
            return redirect("products:category_list")
    else:
        form = ProductCategoryForm()

    return render(request, "products/category_form.html", {"form": form, "business": business, "title": "Add Category"})


@login_required
def product_list(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before managing products.")
        return redirect("businesses:create")

    products = Product.objects.filter(business=business).select_related("category")
    return render(request, "products/product_list.html", {"business": business, "products": products})


@login_required
def product_create(request):
    business = get_active_business(request, request.user)
    if business is None:
        messages.info(request, "Create a business before managing products.")
        return redirect("businesses:create")

    if request.method == "POST":
        form = ProductForm(request.POST, business=business)
        if form.is_valid():
            product = form.save(commit=False)
            product.business = business
            product.created_by = request.user
            product.save()
            messages.success(request, f"Product '{product.name}' created.")
            return redirect("products:product_list")
    else:
        form = ProductForm(business=business)

    return render(request, "products/product_form.html", {"form": form, "business": business, "title": "Add Product"})


@login_required
def product_detail(request, product_id):
    business = get_active_business(request, request.user)
    product = get_object_or_404(Product.objects.select_related("category", "business"), pk=product_id, business=business)
    return render(request, "products/product_detail.html", {"business": business, "product": product})


@login_required
def product_edit(request, product_id):
    business = get_active_business(request, request.user)
    product = get_object_or_404(Product.objects.select_related("category"), pk=product_id, business=business)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product, business=business)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' updated.")
            return redirect("products:product_detail", product_id=product.pk)
    else:
        form = ProductForm(instance=product, business=business)

    return render(request, "products/product_form.html", {"form": form, "business": business, "title": "Edit Product"})
