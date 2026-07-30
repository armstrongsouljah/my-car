import uuid

from dateutil.relativedelta import relativedelta
from django.db import models, transaction
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
        is_new = self._state.adding
        with transaction.atomic():
            if not is_new:
                # Lock the existing row so concurrent saves to the same
                # service serialize instead of racing on the linked-expense
                # upsert below (last save to acquire the lock wins cleanly,
                # rather than an in-flight older save clobbering a newer one).
                ServiceRecord.objects.select_for_update().filter(pk=self.pk).first()
            super().save(*args, **kwargs)
            # A fresh service reading moves the car's odometer forward.
            self.car.record_odometer(self.odometer_km)
            self._sync_expense()
            self._sync_reminder()

    def _sync_expense(self):
        """
        A costed service is also a car expense — keep a linked Expense in
        sync so it shows up in the expense log and month-on-month analytics
        without the owner re-entering the same amount. Dropping the cost
        (or logging one with none) removes any previously-linked expense.
        """
        from expenses.models import Expense

        if self.cost is None:
            Expense.objects.filter(service_record=self).delete()
            return

        Expense.objects.update_or_create(
            service_record=self,
            defaults={
                "car": self.car,
                "category": Constants.EXPENSE_CATEGORY_GARAGE,
                "amount": self.cost,
                "expense_date": self.service_date,
                "vendor": self.garage_name,
                "description": self.description or f"{self.get_service_type_display()} service",
                "odometer_km": self.odometer_km,
            },
        )

    def _sync_reminder(self):
        """
        Some service types have a matching catalog Reminder (see
        reminders/catalog.py) that tracks the same maintenance item — keep
        it in sync with the latest logged service of that type so the
        owner doesn't have to re-enter the same odometer/date by hand in
        the separate Reminders UI. Scoped to service types with a catalog
        mapping (currently just oil changes).
        """
        from reminders.catalog import SERVICE_TYPE_CATALOG_KEYS, get_catalog_item
        from reminders.models import Reminder

        catalog_key = SERVICE_TYPE_CATALOG_KEYS.get(self.service_type)
        if not catalog_key:
            return

        catalog_item = get_catalog_item(catalog_key)
        # Use the latest record of this service type, not necessarily self —
        # editing an older record shouldn't move the reminder's baseline
        # backwards past a more recent one.
        latest = (
            ServiceRecord.objects
            .filter(car=self.car, service_type=self.service_type)
            .order_by("-service_date", "-created_at")
            .first()
        )

        reminder, created = Reminder.objects.get_or_create(
            car=self.car,
            catalog_key=catalog_key,
            defaults={
                "title": catalog_item["title"],
                "category": catalog_item["category"],
                "is_essential": catalog_item["is_essential"],
                "tracking_method": catalog_item["suggested_method"],
            },
        )

        reminder.baseline_odometer_km = latest.odometer_km
        reminder.baseline_date = latest.service_date
        # Only take over the interval fields if they're still at the catalog
        # default (or the reminder is brand new) — an owner who deliberately
        # customized the interval away from the default keeps their value.
        if created or reminder.interval_km == catalog_item["default_interval_km"]:
            reminder.interval_km = latest.interval_km
        if created or reminder.interval_months == catalog_item["default_interval_months"]:
            reminder.interval_months = latest.interval_months
        reminder.save()
