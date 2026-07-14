import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Car",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("make", models.CharField(max_length=100)),
                ("model", models.CharField(max_length=100)),
                ("year", models.PositiveIntegerField(blank=True, null=True)),
                ("registration_number", models.CharField(blank=True, max_length=30)),
                ("vin", models.CharField(blank=True, max_length=50)),
                ("color", models.CharField(blank=True, max_length=50)),
                (
                    "fuel_type",
                    models.CharField(
                        choices=[
                            ("petrol", "Petrol"),
                            ("diesel", "Diesel"),
                            ("hybrid", "Hybrid"),
                            ("electric", "Electric"),
                        ],
                        default="petrol",
                        max_length=20,
                    ),
                ),
                ("current_odometer_km", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cars",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="car",
            constraint=models.UniqueConstraint(
                condition=models.Q(("registration_number", ""), _negated=True),
                fields=("owner", "registration_number"),
                name="unique_owner_registration_number",
            ),
        ),
    ]
