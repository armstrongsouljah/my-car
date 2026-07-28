import secrets
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.crypto import salted_hmac

from utils import Constants


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", Constants.USER_ROLE_OWNER)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Constants.USER_ROLE_ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=Constants.USER_ROLES, default=Constants.USER_ROLE_OWNER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    # Account-level nudge to keep odometer readings fresh (off/daily/weekly/monthly).
    mileage_reminder_frequency = models.CharField(
        max_length=10,
        choices=Constants.MILEAGE_REMINDER_FREQUENCIES,
        default=Constants.MILEAGE_REMINDER_OFF,
    )
    last_mileage_reminder_at = models.DateTimeField(null=True, blank=True)
    # Claim lease for an in-flight mileage-reminder send, set by the daily
    # sweep *before* dispatching the actual send task — distinct from
    # last_mileage_reminder_at, which is only set once the send actually
    # succeeds. Lets a lost/failed send be retried once the lease goes stale
    # (Constants.REMINDER_CLAIM_LEASE_HOURS) rather than being silently
    # dropped forever. See tasks.send_mileage_reminders_task.
    mileage_reminder_queued_at = models.DateTimeField(null=True, blank=True)

    date_joined = models.DateTimeField(default=timezone.now)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    # Set once the day-15 "your account will be deleted soon" reminder has
    # actually been *sent* (not just claimed), so the daily sweep doesn't
    # resend it on every subsequent run before the purge sweep finally
    # deletes the account.
    deletion_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    # Same claim-lease role as mileage_reminder_queued_at above, for the
    # deletion reminder. See tasks.send_account_deletion_reminder_task.
    deletion_reminder_queued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        return self.role == Constants.USER_ROLE_ADMIN

    def deactivate(self):
        """Soft-deactivates the account; the owner can be reactivated by support."""
        self.is_active = False
        self.deactivated_at = timezone.now()
        # Cleared so a user reactivated by support and later deactivated again
        # gets the 15-day reminder on this new lifecycle too, instead of it
        # being silently skipped because a previous lifecycle already sent
        # (or merely claimed) one.
        self.deletion_reminder_sent_at = None
        self.deletion_reminder_queued_at = None
        self.save(
            update_fields=[
                "is_active",
                "deactivated_at",
                "deletion_reminder_sent_at",
                "deletion_reminder_queued_at",
                "updated_at",
            ]
        )


class EmailVerificationOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    # Stores an HMAC of the code, never the code itself. A plain hash would be
    # pointless here — the whole 6-digit space can be hashed in under a second
    # — so this is keyed on SECRET_KEY, which a database-only leak doesn't
    # include. The raw code exists only in the verification email.
    otp = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    # A 6-digit code is only 10^6 wide — without a cap on wrong guesses the
    # whole space is walkable inside the expiry window.
    failed_attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Email Verification OTP"

    def is_expired(self):
        return timezone.now() > self.expires_at

    @staticmethod
    def hash_otp(raw_otp):
        # Pinned explicitly: salted_hmac()'s default digest is SHA1 today but
        # is set to become SHA256 in Django 7.0, which would silently
        # invalidate every pending OTP stored under the old default.
        return salted_hmac("accounts.EmailVerificationOTP", str(raw_otp), algorithm="sha256").hexdigest()

    def verify(self, raw_otp):
        # Constant-time compare so a wrong code can't be narrowed down by timing.
        return secrets.compare_digest(self.otp, self.hash_otp(raw_otp))

    def register_failed_attempt(self):
        """
        Count a wrong guess and burn the code once the cap is hit, so the owner
        has to request a fresh one. Returns True if the code is now spent.

        Uses an atomic F() update rather than `self.failed_attempts += 1` —
        two verify requests racing the same OTP would otherwise both read the
        same stale count and one increment would be lost, letting an attacker
        get more than OTP_MAX_FAILED_ATTEMPTS guesses by parallelizing.
        """
        type(self).objects.filter(pk=self.pk).update(failed_attempts=models.F("failed_attempts") + 1)
        self.refresh_from_db(fields=["failed_attempts"])
        exhausted = self.failed_attempts >= Constants.OTP_MAX_FAILED_ATTEMPTS
        if exhausted and not self.is_used:
            self.is_used = True
            self.save(update_fields=["is_used"])
        return exhausted

    @classmethod
    def create_for_user(cls, user):
        from utils.Email import generate_otp

        expiry_minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 10)

        # Invalidate any existing unused OTPs for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        raw_otp = generate_otp()
        instance = cls.objects.create(
            user=user,
            otp=cls.hash_otp(raw_otp),
            expires_at=timezone.now() + timezone.timedelta(minutes=expiry_minutes),
        )
        # The raw code is returned once, for the email, and never stored.
        return instance, raw_otp


class PasswordResetOTP(models.Model):
    """
    Mirrors EmailVerificationOTP's mechanics (HMAC storage, expiry, capped
    wrong guesses) but is a distinct model with its own HMAC label — a leaked
    verification-OTP hash for a user shouldn't double as a valid
    password-reset hash for the same user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_otps")
    otp = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    failed_attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Password Reset OTP"

    def is_expired(self):
        return timezone.now() > self.expires_at

    @staticmethod
    def hash_otp(raw_otp):
        return salted_hmac("accounts.PasswordResetOTP", str(raw_otp), algorithm="sha256").hexdigest()

    def verify(self, raw_otp):
        return secrets.compare_digest(self.otp, self.hash_otp(raw_otp))

    def register_failed_attempt(self):
        type(self).objects.filter(pk=self.pk).update(failed_attempts=models.F("failed_attempts") + 1)
        self.refresh_from_db(fields=["failed_attempts"])
        exhausted = self.failed_attempts >= Constants.OTP_MAX_FAILED_ATTEMPTS
        if exhausted and not self.is_used:
            self.is_used = True
            self.save(update_fields=["is_used"])
        return exhausted

    @classmethod
    def create_for_user(cls, user):
        from utils.Email import generate_otp

        expiry_minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 10)

        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        raw_otp = generate_otp()
        instance = cls.objects.create(
            user=user,
            otp=cls.hash_otp(raw_otp),
            expires_at=timezone.now() + timezone.timedelta(minutes=expiry_minutes),
        )
        return instance, raw_otp
