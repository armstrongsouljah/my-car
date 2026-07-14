import uuid

from django.conf import settings
from django.db import models

from utils import Constants


def car_photo_path(instance, filename):
    return f"car_photos/{instance.owner_id}/{filename}"


class Car(models.Model):
    """
    A vehicle owned and tracked by a car owner. Owners can register as many
    cars as they like.

    Future: GPS tracking — a `tracker` relation will hang off this model once
    tracking chips / sourced GPS trackers are integrated.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cars")

    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField(null=True, blank=True)
    registration_number = models.CharField(max_length=30, blank=True)
    vin = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    fuel_type = models.CharField(max_length=20, choices=Constants.FUEL_TYPES, default=Constants.FUEL_TYPE_PETROL)

    photo = models.ImageField(upload_to=car_photo_path, null=True, blank=True)

    current_odometer_km = models.PositiveIntegerField(default=0)
    odometer_updated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "registration_number"],
                condition=~models.Q(registration_number=""),
                name="unique_owner_registration_number",
            ),
        ]

    def __str__(self):
        label = f"{self.make} {self.model}"
        if self.year:
            label = f"{label} ({self.year})"
        if self.registration_number:
            label = f"{label} — {self.registration_number}"
        return label

    def record_odometer(self, odometer_km):
        """Moves the odometer forward; readings never go backwards."""
        from django.utils import timezone

        if odometer_km and odometer_km > self.current_odometer_km:
            self.current_odometer_km = odometer_km
            self.odometer_updated_at = timezone.now()
            self.save(update_fields=["current_odometer_km", "odometer_updated_at", "updated_at"])
