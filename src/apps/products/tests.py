from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.businesses.models import Business, BusinessUser
from apps.products.models import Product, ProductCategory


class ProductBusinessScopeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tenant-owner",
            email="owner@example.com",
            password="StrongPass123!",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-user",
            email="other@example.com",
            password="StrongPass123!",
        )
        self.business = Business.objects.create(name="Alpha Holdings", owner=self.user)
        BusinessUser.objects.create(business=self.business, user=self.user, role=BusinessUser.Role.OWNER)
        self.other_business = Business.objects.create(name="Beta Holdings", owner=self.other_user)
        BusinessUser.objects.create(business=self.other_business, user=self.other_user, role=BusinessUser.Role.OWNER)
        self.category = ProductCategory.objects.create(business=self.business, name="Cleaning")

    def test_product_is_scoped_to_business(self):
        product = Product.objects.create(
            business=self.business,
            category=self.category,
            name="Glass Cleaner",
            sku="GLC-100",
            unit_of_measure="bottle",
            cost_price=12.50,
            selling_price=18.00,
            reorder_level=5,
        )

        self.assertEqual(Product.objects.filter(business=self.business).count(), 1)
        self.assertNotIn(product, Product.objects.filter(business=self.other_business))

    def test_products_urls_resolve(self):
        from django.urls import reverse
        self.assertEqual(reverse("products:product_list"), "/products/")
        self.assertEqual(reverse("products:product_create"), "/products/add/")

