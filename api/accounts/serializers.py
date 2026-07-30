from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import serializers, status

from accounts.models import EmailVerificationOTP, PasswordResetOTP, User
from utils import Constants
from utils.Exception import CustomValidation
from utils.Serializers import BaseModelSerializer, CreateModelSerializer, EditModelSerializer, ListModelSerializer

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterSerializer(CreateModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone", "password", "country")
        extra_kwargs = {
            "first_name": {"required": False, "default": ""},
            "last_name": {"required": False, "default": ""},
            "phone": {"required": False, "default": ""},
            "country": {"required": False, "default": ""},
            # DRF derives a UniqueValidator from the model's unique=True, which
            # would answer "already exists" and reintroduce the enumeration
            # oracle. RegisterView does the duplicate check itself.
            "email": {"validators": []},
        }

    def validate_email(self, value):
        # Deliberately no "already registered" check here — that answer is an
        # account-existence oracle. RegisterView handles the duplicate case by
        # returning the same response either way and emailing the address that
        # already owns the account.
        return value.lower()

    def validate(self, attrs):
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        # See #40: `currency` isn't user-supplied at signup, it's derived
        # from `country` — an unrecognized/blank country just leaves it
        # unset, same as an existing pre-#40 account.
        country = validated_data.get("country") or ""
        validated_data["currency"] = Constants.COUNTRY_TO_CURRENCY.get(country, "")
        return User.objects.create_user(**validated_data)


# ---------------------------------------------------------------------------
# OTP — Verify Email
# ---------------------------------------------------------------------------

class VerifyEmailSerializer(serializers.Serializer):
    """
    Every failure path returns the same message. Distinguishing "no such
    account" from "already verified" from "wrong code" would turn this endpoint
    into an account-existence oracle, and the remedy the caller needs is
    identical in each case: request a fresh code.
    """
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)

    INVALID = "That code is invalid or has expired. Please request a new one."

    def _reject(self):
        raise CustomValidation(self.INVALID, field="otp", status_code=status.HTTP_400_BAD_REQUEST)

    def validate(self, attrs):
        email = attrs["email"].lower()
        raw_otp = attrs["otp"]

        user = User.objects.filter(email=email).first()
        if user is None or user.is_email_verified:
            self._reject()

        otp_instance = (
            EmailVerificationOTP.objects
            .filter(user=user, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if not otp_instance or otp_instance.is_expired():
            self._reject()

        if not otp_instance.verify(raw_otp):
            # Burns the code once the attempt cap is hit; the caller is told to
            # request a new one either way.
            otp_instance.register_failed_attempt()
            self._reject()

        attrs["user"] = user
        attrs["otp_instance"] = otp_instance
        return attrs


# ---------------------------------------------------------------------------
# OTP — Resend
# ---------------------------------------------------------------------------

class ResendOTPSerializer(serializers.Serializer):
    """
    Resolves the target account without ever reporting whether it exists —
    `user` comes back as None for an unknown or already-verified address and
    the view returns the same response regardless.
    """
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"].lower()
        attrs["user"] = User.objects.filter(email=email, is_email_verified=False).first()
        return attrs


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["email"].lower(), password=attrs["password"])
        if not user:
            raise CustomValidation(
                "Invalid email or password.",
                field="non_field_errors",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            raise CustomValidation(
                "This account has been deactivated.",
                field="non_field_errors",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if not user.is_email_verified:
            raise CustomValidation(
                "Please verify your email before logging in. Check your inbox for the OTP.",
                field="non_field_errors",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        attrs["user"] = user
        return attrs


# ---------------------------------------------------------------------------
# Profile (read + update)
# ---------------------------------------------------------------------------

class UserProfileSerializer(BaseModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "phone",
            "mileage_reminder_frequency", "country", "currency",
        )
        read_only_fields = ("id", "email")

    @staticmethod
    def select_related_fields():
        return []


class UpdateProfileSerializer(EditModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "mileage_reminder_frequency", "country", "currency")


class UserListSerializer(ListModelSerializer):
    """Admin-only account listing (both owners and admins)."""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "full_name",
            "phone", "role", "is_active", "is_email_verified", "date_joined",
        )


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise CustomValidation(
                "Current password is incorrect.",
                field="current_password",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise CustomValidation(
                "New passwords do not match.",
                field="confirm_new_password",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        validate_password(attrs["new_password"], user)
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user


# ---------------------------------------------------------------------------
# Password reset — request
# ---------------------------------------------------------------------------

class RequestPasswordResetSerializer(serializers.Serializer):
    """
    Resolves the target account without ever reporting whether it exists —
    like ResendOTPSerializer, `user` comes back None for an unknown or
    deactivated address and the view returns the same response regardless.
    """
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"].lower()
        attrs["user"] = User.objects.filter(email=email, is_active=True).first()
        return attrs


# ---------------------------------------------------------------------------
# Password reset — confirm
# ---------------------------------------------------------------------------

class ResetPasswordSerializer(serializers.Serializer):
    """
    Every failure path returns the same message — see VerifyEmailSerializer's
    docstring; the same account-existence oracle risk applies here.
    """
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True)

    INVALID = "That code is invalid or has expired. Please request a new one."

    def _reject(self):
        raise CustomValidation(self.INVALID, field="otp", status_code=status.HTTP_400_BAD_REQUEST)

    def validate(self, attrs):
        email = attrs["email"].lower()
        raw_otp = attrs["otp"]

        user = User.objects.filter(email=email, is_active=True).first()
        if user is None:
            self._reject()

        otp_instance = (
            PasswordResetOTP.objects
            .filter(user=user, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if not otp_instance or otp_instance.is_expired():
            self._reject()

        if not otp_instance.verify(raw_otp):
            otp_instance.register_failed_attempt()
            self._reject()

        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise CustomValidation(
                "New passwords do not match.",
                field="confirm_new_password",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        validate_password(attrs["new_password"], user)

        attrs["user"] = user
        attrs["otp_instance"] = otp_instance
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        otp_instance = self.validated_data["otp_instance"]

        otp_instance.is_used = True
        otp_instance.save(update_fields=["is_used"])

        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user


# ---------------------------------------------------------------------------
# Google OAuth — frontend sends the Google ID token; we verify it here
# ---------------------------------------------------------------------------

class GoogleAuthSerializer(serializers.Serializer):
    """
    Accepts a Google ID token (obtained client-side via Google Sign-In / One Tap).
    Verifies it with Google, then finds-or-creates the local user.
    Google users are already verified — no OTP needed.
    """
    id_token = serializers.CharField(write_only=True)

    def validate(self, attrs):
        token = attrs["id_token"]
        client_id = settings.GOOGLE_OAUTH_CLIENT_ID

        if not client_id:
            raise CustomValidation(
                "Google OAuth is not configured on this server.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            payload = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                client_id,
            )
        except ValueError:
            raise CustomValidation(
                "Invalid or expired Google token.",
                field="id_token",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        email = payload.get("email", "").lower()
        if not email:
            raise CustomValidation(
                "Google account has no associated email address.",
                field="id_token",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": payload.get("given_name", ""),
                "last_name": payload.get("family_name", ""),
                "is_email_verified": True,
            },
        )

        if not created and not user.is_active:
            raise CustomValidation(
                "This account has been deactivated.",
                field="non_field_errors",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if not created and not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        attrs["user"] = user
        return attrs


# ---------------------------------------------------------------------------
# Deactivate Account
# ---------------------------------------------------------------------------

class DeactivateAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate(self, attrs):
        user = self.context["request"].user

        # Google-only accounts have no usable password — let them deactivate freely.
        if user.has_usable_password():
            if not attrs.get("password"):
                raise CustomValidation(
                    "Password is required to deactivate your account.",
                    field="password",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if not user.check_password(attrs["password"]):
                raise CustomValidation(
                    "Password is incorrect.",
                    field="password",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        return attrs
