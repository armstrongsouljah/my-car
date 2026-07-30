import uuid

from django.db import models
from django.utils import timezone

from cars.models import Car
from utils import Constants


class Expense(models.Model):
    """
    A car-related expense — garage visit, modification parts, fuel, and so on.
    Feeds the month-on-month analytics endpoint.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="expenses")

    # Set when this expense was auto-generated from a costed ServiceRecord
    # (see ServiceRecord.save()) — cascades so deleting the service removes
    # its expense too, and lets the sync logic find/update the existing row.
    service_record = models.OneToOneField(
        "services.ServiceRecord", on_delete=models.CASCADE, null=True, blank=True, related_name="expense",
    )

    category = models.CharField(max_length=30, choices=Constants.EXPENSE_CATEGORIES, default=Constants.EXPENSE_CATEGORY_OTHER)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(default=timezone.localdate)
    vendor = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)

    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    litres = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Fuel expenses only")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return f"{self.get_category_display()} — {self.amount} on {self.expense_date} ({self.car})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.odometer_km:
            self.car.record_odometer(self.odometer_km)


class MonthlyExpenseReportDelivery(models.Model):
    """
    Idempotency record for the monthly expense report email (see #21): one
    row per user per calendar period, written only after the send actually
    succeeds. Unlike the daily reminder sweeps (mileage/deletion/verify —
    see #27), a failed monthly send has no next-day retry of the same
    underlying condition to fall back on — next month's sweep targets a
    different period entirely. This row is what lets a redelivered or
    manually re-run task recognize "already sent" and skip re-sending,
    while a period with no row for a user is still open to a retry (a
    re-run of the sweep, today or later) rather than being silently lost.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="monthly_expense_report_deliveries"
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "year", "month"], name="unique_monthly_expense_report_delivery"),
        ]
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.user_id} — {self.year}-{self.month:02d}"
