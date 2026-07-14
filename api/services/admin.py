from django.contrib import admin

from services.models import ServiceRecord


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    list_display = ("__str__", "service_date", "next_due_odometer_km", "next_due_date", "cost")
    list_filter = ("service_type",)
    search_fields = ("car__make", "car__model", "car__registration_number", "garage_name")
