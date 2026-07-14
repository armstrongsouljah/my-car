import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import inspections.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("cars", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Inspection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("inspection_date", models.DateField(default=django.utils.timezone.localdate)),
                ("odometer_km", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("passed", "Passed"),
                            ("advisories", "Passed with Advisories"),
                            ("failed", "Failed"),
                        ],
                        default="passed",
                        max_length=20,
                    ),
                ),
                ("inspector_name", models.CharField(blank=True, max_length=150)),
                ("notes", models.TextField(blank=True)),
                (
                    "report",
                    models.FileField(blank=True, null=True, upload_to=inspections.models.inspection_report_path),
                ),
                ("next_inspection_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "car",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inspections",
                        to="cars.car",
                    ),
                ),
            ],
            options={
                "ordering": ["-inspection_date", "-created_at"],
            },
        ),
    ]
