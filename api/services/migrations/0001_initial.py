import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("cars", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "service_type",
                    models.CharField(
                        choices=[
                            ("minor_service", "Minor Service"),
                            ("major_service", "Major Service"),
                            ("oil_change", "Oil Change"),
                            ("brakes", "Brakes"),
                            ("tyres", "Tyres"),
                            ("battery", "Battery"),
                            ("other", "Other"),
                        ],
                        default="minor_service",
                        max_length=30,
                    ),
                ),
                ("service_date", models.DateField(default=django.utils.timezone.localdate)),
                ("odometer_km", models.PositiveIntegerField()),
                ("garage_name", models.CharField(blank=True, max_length=150)),
                ("description", models.TextField(blank=True)),
                ("cost", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("interval_km", models.PositiveIntegerField(blank=True, help_text="e.g. 5000 or 10000", null=True)),
                ("interval_months", models.PositiveIntegerField(blank=True, help_text="e.g. 6 or 12", null=True)),
                ("next_due_odometer_km", models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ("next_due_date", models.DateField(blank=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "car",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_records",
                        to="cars.car",
                    ),
                ),
            ],
            options={
                "ordering": ["-service_date", "-created_at"],
            },
        ),
    ]
