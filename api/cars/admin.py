from django.contrib import admin

from cars.models import Car


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("__str__", "owner", "current_odometer_km", "is_active", "created_at")
    list_filter = ("is_active", "fuel_type", "make")
    search_fields = ("make", "model", "registration_number", "vin", "owner__email")
