import functools
import uuid

from django.db import models
from django.utils import timezone

from utils import Constants
from utils.Uploads import validate_upload_size, validate_upload_type

from cars.models import Car


def inspection_report_path(instance, filename):
    return f"inspection_reports/{instance.car_id}/{filename}"


class Inspection(models.Model):
    """
    A general inspection so the owner knows the state of their vehicle.
    The inspection report upload is optional.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="inspections")

    inspection_date = models.DateField(default=timezone.localdate)
    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Constants.INSPECTION_STATUSES, default=Constants.INSPECTION_STATUS_PASSED)
    inspector_name = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    report = models.FileField(
        upload_to=inspection_report_path,
        null=True,
        blank=True,
        validators=[
            validate_upload_type,
            functools.partial(validate_upload_size, max_size_mb=Constants.INSPECTION_REPORT_MAX_SIZE_MB),
        ],
    )

    # When the next inspection should happen; defaults to
    # INSPECTION_DEFAULT_INTERVAL_MONTHS after inspection_date when omitted.
    next_inspection_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-inspection_date", "-created_at"]

    def __str__(self):
        return f"Inspection — {self.car} on {self.inspection_date}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.odometer_km:
            self.car.record_odometer(self.odometer_km)
