from django.contrib import admin

from support.models import SupportRequest, SupportAttachment


class SupportAttachmentInline(admin.TabularInline):
    model = SupportAttachment
    extra = 0
    readonly_fields = ("file", "uploaded_at")


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "subject", "user")
    list_filter = ("subject", "created_at")
    search_fields = ("name", "email", "message", "custom_subject")
    readonly_fields = ("id", "created_at")
    inlines = [SupportAttachmentInline]
