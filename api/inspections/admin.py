from django.contrib import admin

from inspections.models import Inspection


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "inspection_date", "next_inspection_date")
    list_filter = ("status",)
    search_fields = ("car__make", "car__model", "car__registration_number", "inspector_name")
