from django.db import migrations, models
import django.db.models.deletion


def attach_personal_properties(apps, schema_editor):
    Property = apps.get_model("businesses", "Property")
    Business = apps.get_model("businesses", "Business")
    BusinessUser = apps.get_model("businesses", "BusinessUser")

    for property_obj in Property.objects.filter(business__isnull=True):
        business = (
            BusinessUser.objects.filter(user_id=property_obj.owner_id)
            .order_by("business_id")
            .values_list("business_id", flat=True)
            .first()
        )
        if business is None:
            business = (
                Business.objects.filter(owner_id=property_obj.owner_id)
                .order_by("id")
                .values_list("id", flat=True)
                .first()
            )
        if business is None:
            property_obj.delete()
        else:
            property_obj.business_id = business
            property_obj.save(update_fields=["business"])


class Migration(migrations.Migration):
    dependencies = [
        ("businesses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="expected_selling_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name="property",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(attach_personal_properties, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="property",
            name="business",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="properties", to="businesses.business"),
        ),
        migrations.AlterField(
            model_name="property",
            name="property_type",
            field=models.CharField(choices=[("LAND", "Land"), ("HOUSE", "House"), ("RESIDENTIAL", "Residential"), ("COMMERCIAL", "Commercial"), ("AGRICULTURAL", "Agricultural"), ("INDUSTRIAL", "Industrial"), ("MIXED_USE", "Mixed use"), ("OTHER", "Other")], default="LAND", max_length=20),
        ),
    ]
