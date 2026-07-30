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
    # ISO 4217, snapshotted from the owner's currency the moment this
    # expense is created (see #40) — never recomputed afterwards, so a
    # later change to the owner's currency can't retroactively change what
    # currency this amount was actually logged in. Blank for pre-#40 rows
    # and for owners who have no currency set; ExpenseListSerializer/
    # ExpenseDetailSerializer's `display_amount` falls back to the raw
    # amount, unconverted, whenever this is blank.
    currency = models.CharField(max_length=3, blank=True)
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
        if self._state.adding and not self.currency:
            self.currency = self.car.owner.currency
        super().save(*args, **kwargs)
        if self.odometer_km:
            self.car.record_odometer(self.odometer_km)


class ExchangeRate(models.Model):
    """
    Daily USD-cross rate snapshot for a currency GlavBox supports (see #40),
    fetched once a day by tasks.refresh_exchange_rates_task from a free,
    keyless FX-rate API. `rate_to_usd` means "1 unit of `currency` is worth
    this many USD" — USD is used as the pivot so any currency can be
    converted to any other via two lookups instead of needing a rate row
    for every currency pair.

    Conversion always uses the latest row for each currency (see
    utils.Currency.convert_amount), not the rate in effect on a given
    expense's own date — simpler, and matches how most personal-finance
    apps show "value in my currency today" rather than tracking historical
    FX drift. Older daily rows are kept anyway, purely as an audit trail.
    """
    date = models.DateField()
    currency = models.CharField(max_length=3)
    rate_to_usd = models.DecimalField(max_digits=20, decimal_places=10)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["date", "currency"], name="unique_exchange_rate_per_day"),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.currency} @ {self.date}: {self.rate_to_usd}"


class MonthlyExpenseReportDelivery(models.Model):
    """
    Claim + delivery record for the monthly expense report email (see #21) —
    same lease shape as User.mileage_reminder_queued_at/last_mileage_reminder_at
    and their deletion/verify-reminder equivalents (see #27), just per period
    instead of per mutable column, since a user accumulates one of these a
    month rather than ever needing just the latest.

    `queued_at` is written the moment a task claims this (user, year, month)
    — atomically, via the unique constraint below, so two concurrent/
    redelivered task executions for the same period can't both proceed to
    send. `sent_at` is only set once the send actually succeeds. A claim
    whose send never confirms (crash, lost task, a raised exception) goes
    stale after Constants.REMINDER_CLAIM_LEASE_HOURS and gets reclaimed by a
    later run — unlike the daily reminder sweeps, a monthly digest has no
    next-day retry of the same underlying condition to fall back on, so
    "stale claim, no sent_at" is what keeps a transient failure from
    silently losing that month's report for good.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="monthly_expense_report_deliveries"
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    queued_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "year", "month"], name="unique_monthly_expense_report_delivery"),
            models.CheckConstraint(
                condition=models.Q(month__gte=1, month__lte=12), name="monthly_expense_report_delivery_valid_month"
            ),
        ]
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.user_id} — {self.year}-{self.month:02d}"
