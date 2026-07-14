import secrets

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import User
from utils import Constants


class Command(BaseCommand):
    help = "Idempotently seeds the super admin account (default: admin@mycar.com). Safe to run on every boot."

    def handle(self, *args, **options):
        email = (settings.ADMIN_EMAIL or "admin@mycar.com").lower()

        if User.objects.filter(email=email).exists():
            self.stdout.write(f"Super admin '{email}' already exists — skipping.")
            return

        password = settings.ADMIN_PASSWORD
        generated = False
        if not password:
            password = secrets.token_urlsafe(12)
            generated = True

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name="Super",
            last_name="Admin",
            role=Constants.USER_ROLE_ADMIN,
        )
        user.is_staff = True
        user.is_superuser = True
        user.is_email_verified = True
        user.save(update_fields=["is_staff", "is_superuser", "is_email_verified"])

        self.stdout.write(self.style.SUCCESS(f"Super admin '{email}' created."))
        if generated:
            # Printed once at first boot; set ADMIN_PASSWORD to control it instead.
            self.stdout.write(self.style.WARNING(f"Generated password: {password} — store it now, it won't be shown again."))
