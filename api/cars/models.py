import uuid

from django.conf import settings
from django.db import models

from utils import Constants


def car_photo_path(instance, filename):
    # No longer used by any field — kept importable because migration 0002
    # references it by path (upload_to=car_photo_path) and Django replays
    # full migration history from a fresh database.
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

    photo_url = models.URLField(max_length=500, null=True, blank=True)

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

    def save(self, *args, **kwargs):
        # See #94 — only on creation, not every save: an owner clearing
        # their photo_url on an existing car via an edit is a deliberate
        # "remove my photo" action, not something to silently revert. Guarded
        # on settings.DEFAULT_PHOTO_URL being set so an environment that
        # hasn't configured one (e.g. a fresh local dev box) just leaves
        # photo_url blank, same as before #94, rather than "setting" it to "".
        if self._state.adding and not self.photo_url and settings.DEFAULT_PHOTO_URL:
            self.photo_url = settings.DEFAULT_PHOTO_URL
        super().save(*args, **kwargs)

    def record_odometer(self, odometer_km, allow_decrease=False):
        """
        Moves the odometer forward; readings never go backwards by default.
        Uses a single conditional UPDATE (rather than compare-then-save) so
        concurrent writers can't race a higher reading back down.

        `allow_decrease` opts out of that guard for the rare legitimate case
        (engine/odometer replacement) — callers must gather explicit owner
        confirmation before passing it, this method doesn't ask why.
        """
        from django.utils import timezone

        from utils import Cache

        if not odometer_km:
            return

        now = timezone.now()
        filters = {"pk": self.pk}
        if not allow_decrease:
            filters["current_odometer_km__lt"] = odometer_km
        updated = Car.objects.filter(**filters).update(
            current_odometer_km=odometer_km, odometer_updated_at=now, updated_at=now,
        )
        if updated:
            self.current_odometer_km = odometer_km
            self.odometer_updated_at = now
            # Reminder/service-digest status is computed against the current
            # odometer reading (see reminders/engine.py, services/reminders.py)
            # on every call site that moves it (car edit, expense/inspection/
            # service save) — not just the cars endpoint's own cache.
            Cache.invalidate_reminders(self.owner_id)
            Cache.invalidate_service_digest(self.owner_id)
