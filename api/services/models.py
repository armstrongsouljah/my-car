import uuid

from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils import timezone

from utils import Constants

from cars.models import Car


class ServiceRecord(models.Model):
    """
    A logged service with an interval rule for the next one, e.g.
    "5,000 km or 6 months, whichever comes first" — both thresholds are
    computed at save time, and the due status is evaluated against whichever
    trips first (see `services/reminders.py`).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="service_records")

    service_type = models.CharField(max_length=30, choices=Constants.SERVICE_TYPES, default=Constants.SERVICE_TYPE_MINOR)
    service_date = models.DateField(default=timezone.localdate)
    odometer_km = models.PositiveIntegerField()
    garage_name = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Interval rule: next service at odometer + interval_km OR service_date +
    # interval_months — whichever comes first. Either side may be omitted.
    interval_km = models.PositiveIntegerField(null=True, blank=True, help_text="e.g. 5000 or 10000")
    interval_months = models.PositiveIntegerField(null=True, blank=True, help_text="e.g. 6 or 12")

    # Denormalised thresholds, computed on save.
    next_due_odometer_km = models.PositiveIntegerField(null=True, blank=True, editable=False)
    next_due_date = models.DateField(null=True, blank=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-service_date", "-created_at"]

    def __str__(self):
        return f"{self.get_service_type_display()} — {self.car} @ {self.odometer_km} km"

    def compute_next_due(self):
        self.next_due_odometer_km = (
            self.odometer_km + self.interval_km if self.interval_km else None
        )
        self.next_due_date = (
            self.service_date + relativedelta(months=self.interval_months)
            if self.interval_months else None
        )

    def save(self, *args, **kwargs):
        self.compute_next_due()
        super().save(*args, **kwargs)
        # A fresh service reading moves the car's odometer forward.
        self.car.record_odometer(self.odometer_km)
