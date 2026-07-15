import uuid

from dateutil.relativedelta import relativedelta
from django.db import models

from utils import Constants

from cars.models import Car


class Reminder(models.Model):
    """
    An owner-configured reminder for a car — either picked from the preset
    catalog (see `reminders/catalog.py`, `catalog_key` set) or fully custom
    (`catalog_key` blank). Tracked by date, by mileage, or by whichever of
    the two comes first, counted from a baseline point (`baseline_*`) —
    mirrors `ServiceRecord`'s "whichever comes first" interval rule
    (`services/models.py`), but the baseline is an explicit field here
    rather than implicitly the logged service's own odometer/date.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="reminders")

    catalog_key = models.CharField(max_length=60, blank=True)
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=Constants.REMINDER_CATEGORIES, default=Constants.REMINDER_CATEGORY_OTHER)
    is_essential = models.BooleanField(default=False)

    tracking_method = models.CharField(
        max_length=20, choices=Constants.REMINDER_TRACKING_METHODS,
        default=Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
    )
    interval_km = models.PositiveIntegerField(null=True, blank=True)
    interval_months = models.PositiveIntegerField(null=True, blank=True)

    # Baseline ("last done at") — the start of the tracked interval / progress bar.
    baseline_odometer_km = models.PositiveIntegerField(null=True, blank=True)
    baseline_date = models.DateField(null=True, blank=True)

    # Denormalised thresholds, computed on save (see compute_next_due()).
    next_due_odometer_km = models.PositiveIntegerField(null=True, blank=True, editable=False)
    next_due_date = models.DateField(null=True, blank=True, editable=False)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.car}"

    def compute_next_due(self):
        needs_km = self.tracking_method in (
            Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
        )
        needs_months = self.tracking_method in (
            Constants.REMINDER_TRACKING_METHOD_DATE,
            Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
        )

        self.next_due_odometer_km = (
            self.baseline_odometer_km + self.interval_km
            if needs_km and self.baseline_odometer_km is not None and self.interval_km is not None else None
        )
        self.next_due_date = (
            self.baseline_date + relativedelta(months=self.interval_months)
            if needs_months and self.baseline_date is not None and self.interval_months is not None else None
        )

    def save(self, *args, **kwargs):
        self.compute_next_due()
        super().save(*args, **kwargs)
