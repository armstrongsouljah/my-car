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
            name="Expense",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("garage_visit", "Garage Visit"),
                            ("modification_parts", "Modification / Parts"),
                            ("fuel", "Fuel"),
                            ("insurance", "Insurance"),
                            ("tax_licensing", "Tax & Licensing"),
                            ("cleaning", "Cleaning & Detailing"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=30,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("expense_date", models.DateField(default=django.utils.timezone.localdate)),
                ("vendor", models.CharField(blank=True, max_length=150)),
                ("description", models.TextField(blank=True)),
                ("odometer_km", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "litres",
                    models.DecimalField(
                        blank=True, decimal_places=2, help_text="Fuel expenses only", max_digits=8, null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "car",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="expenses",
                        to="cars.car",
                    ),
                ),
            ],
            options={
                "ordering": ["-expense_date", "-created_at"],
            },
        ),
    ]
