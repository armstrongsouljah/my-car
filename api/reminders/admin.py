from django.contrib import admin

from reminders.models import Reminder


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "car", "category", "is_essential", "tracking_method", "next_due_odometer_km", "next_due_date")
    list_filter = ("category", "is_essential", "tracking_method")
    search_fields = ("title", "car__make", "car__model", "car__registration_number")
