from django.contrib import admin

from accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "role", "is_active", "is_email_verified", "date_joined")
    list_filter = ("role", "is_active", "is_email_verified")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)


# EmailVerificationOTP is deliberately not registered. The codes are stored as
# HMAC digests now, so there is nothing useful to read here, and an admin
# listing of live verification codes is not something worth having.
