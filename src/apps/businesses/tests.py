from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Business, BusinessUser, Property


class PropertyBusinessScopeTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="StrongPass123!",
        )
        self.other_user = user_model.objects.create_user(
            username="other",
            email="other@example.com",
            password="StrongPass123!",
        )
        self.business = Business.objects.create(name="Alpha Holdings", owner=self.user)
        BusinessUser.objects.create(business=self.business, user=self.user, role=BusinessUser.Role.OWNER)
        self.other_business = Business.objects.create(name="Beta Holdings", owner=self.other_user)
        BusinessUser.objects.create(business=self.other_business, user=self.other_user, role=BusinessUser.Role.OWNER)
        self.client.force_login(self.user)
        self.session = self.client.session
        self.session["active_business_id"] = self.business.pk
        self.session.save()

    def property_data(self):
        return {
            "business": self.business.pk,
            "name": "Riverside Plot",
            "address": "12 River Road",
            "area": "2500",
            "property_type": Property.PropertyType.LAND,
            "ownership_status": Property.OwnershipStatus.OWNED,
            "purchase_price": "100000",
            "current_estimated_value": "125000",
            "expected_selling_price": "150000",
            "purchase_date": "2026-01-15",
            "notes": "Near planned transit route.",
        }

    def test_property_creation_and_dashboard_totals(self):
        response = self.client.post(reverse("businesses:property_create"), self.property_data())
        property_obj = Property.objects.get(name="Riverside Plot")

        self.assertRedirects(response, reverse("businesses:property_list"))
        self.assertEqual(property_obj.business, self.business)
        dashboard = self.client.get(reverse("businesses:property_list"))
        self.assertContains(dashboard, "125000.00")
        self.assertContains(dashboard, "50000.00")

    def test_crud_operations(self):
        property_obj = Property.objects.create(
            business=self.business,
            owner=self.user,
            name="Old Name",
            area=Decimal("100"),
        )
        detail = reverse("businesses:property_detail", args=[property_obj.pk])
        edit = reverse("businesses:property_edit", args=[property_obj.pk])
        delete = reverse("businesses:property_delete", args=[property_obj.pk])

        self.assertEqual(self.client.get(detail).status_code, 200)
        updated = self.property_data() | {"name": "Updated Name"}
        self.assertRedirects(self.client.post(edit, updated), detail)
        self.assertTrue(Property.objects.filter(name="Updated Name").exists())
        self.assertRedirects(self.client.post(delete), reverse("businesses:property_list"))
        self.assertFalse(Property.objects.filter(pk=property_obj.pk).exists())

    def test_unauthorized_user_cannot_access_another_business_property(self):
        property_obj = Property.objects.create(
            business=self.other_business,
            owner=self.other_user,
            name="Private Parcel",
        )
        for name in ("property_detail", "property_edit", "property_delete"):
            response = self.client.get(reverse(f"businesses:{name}", args=[property_obj.pk]))
            self.assertEqual(response.status_code, 404)

        self.assertNotContains(self.client.get(reverse("businesses:property_list")), "Private Parcel")