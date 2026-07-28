from django.contrib import admin

from support.models import SupportRequest


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "subject", "user")
    list_filter = ("subject", "created_at")
    search_fields = ("name", "email", "message", "custom_subject")
    # Attachment contents live only in the support inbox — this lists the
    # filenames that were sent so the two can be matched up.
    readonly_fields = ("id", "created_at", "attachment_names")
