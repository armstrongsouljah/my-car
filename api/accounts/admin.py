from django.contrib import admin

from accounts.models import User, EmailVerificationOTP


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "role", "is_active", "is_email_verified", "date_joined")
    list_filter = ("role", "is_active", "is_email_verified")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)


@admin.register(EmailVerificationOTP)
class EmailVerificationOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "is_used")
    list_filter = ("is_used",)
