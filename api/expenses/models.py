import uuid

from django.db import models
from django.utils import timezone

from utils import Constants

from cars.models import Car


class Expense(models.Model):
    """
    A car-related expense — garage visit, modification parts, fuel, and so on.
    Feeds the month-on-month analytics endpoint.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="expenses")

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
