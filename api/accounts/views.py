from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from utils.Views import SmartAPIView, SmartDetailView, SmartPaginationAPIView
from utils.Permissions import IsAdminPermission

from accounts.models import User, EmailVerificationOTP
from accounts.throttles import (
    LoginRateThrottle,
    RegisterRateThrottle,
    ResendOTPRateThrottle,
    VerifyOTPRateThrottle,
)
from accounts.serializers import (
    RegisterSerializer,
    LoginSerializer,
    VerifyEmailSerializer,
    ResendOTPSerializer,
    UserProfileSerializer,
    UpdateProfileSerializer,
    ChangePasswordSerializer,
    GoogleAuthSerializer,
    DeactivateAccountSerializer,
    UserListSerializer,
)


def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def _dispatch_otp(user):
    """Create an OTP record and fire the Celery email task."""
    from tasks import send_otp_email_task

    _, raw_otp = EmailVerificationOTP.create_for_user(user)
    send_otp_email_task.delay(
        email=user.email,
        otp=raw_otp,
        first_name=user.first_name,
    )


def _notify_existing_account(existing):
    """
    Called when a register request targets an address that already has an
    account. Same response either way, so telling the caller which branch ran
    would recreate the enumeration oracle — only the address owner is told.
    """
    if existing.is_email_verified:
        # The owner can act on this directly, so point them at login.
        from tasks import send_duplicate_signup_email_task

        send_duplicate_signup_email_task.delay(email=existing.email, first_name=existing.first_name)
    else:
        # Never verified the first time around — most likely they lost the
        # original code and are retrying the signup form. A "sign in instead"
        # email would be a dead end since login rejects unverified accounts,
        # so just re-issue a code the same way a fresh signup would.
        # create_for_user() invalidates the old one.
        _dispatch_otp(existing)


# ---------------------------------------------------------------------------
# Register — creates account, sends OTP; no tokens until verified
# ---------------------------------------------------------------------------

class RegisterView(SmartAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        existing = User.objects.filter(email=email).first()
        if existing is not None:
            _notify_existing_account(existing)
        else:
            try:
                with transaction.atomic():
                    new_user = serializer.save()
            except IntegrityError:
                # Lost a race with a concurrent signup for this address (e.g. a
                # double-clicked submit): the DB's unique constraint is the
                # only backstop left now that the pre-save UniqueValidator is
                # gone — it was itself an enumeration oracle. Only treat this
                # as that race if the email row genuinely exists now; a
                # collision on some other unique field wouldn't have one, and
                # swallowing that would hide a real error behind a 201.
                winner = User.objects.filter(email=email).first()
                if winner is None:
                    raise
                _notify_existing_account(winner)
            else:
                _dispatch_otp(new_user)

        return self.respond_with(
            f"Check your inbox — we've sent a message to {email}.",
            status_code=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Verify Email — validates OTP, marks account verified, returns tokens
# ---------------------------------------------------------------------------

class VerifyEmailView(SmartAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [VerifyOTPRateThrottle]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        otp_instance = serializer.validated_data["otp_instance"]

        otp_instance.is_used = True
        otp_instance.save(update_fields=["is_used"])

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        from tasks import send_welcome_email_task
        send_welcome_email_task.delay(email=user.email, first_name=user.first_name)

        tokens = _get_tokens(user)
        return Response(
            {"user": UserProfileSerializer(user).data, "tokens": tokens},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Resend OTP
# ---------------------------------------------------------------------------

class ResendOTPView(SmartAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [ResendOTPRateThrottle]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # `user` is None for an unknown or already-verified address. Nothing is
        # sent in that case, but the response is identical either way.
        if user is not None:
            _dispatch_otp(user)

        email = serializer.validated_data["email"].lower()
        return self.respond_with(
            f"If {email} needs verifying, a new code is on its way to it."
        )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginView(SmartAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = _get_tokens(user)
        return Response(
            {"user": UserProfileSerializer(user).data, "tokens": tokens},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Logout — blacklists the refresh token
# ---------------------------------------------------------------------------

class LogoutView(SmartAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return self.respond_with("refresh token is required.", status_code=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return self.respond_with("Token is invalid or already expired.", status_code=status.HTTP_400_BAD_REQUEST)
        return self.respond_with("Successfully logged out.")


# ---------------------------------------------------------------------------
# Google OAuth — accepts a Google ID token from the frontend
# ---------------------------------------------------------------------------

class GoogleAuthView(SmartAPIView):
    permission_classes = [AllowAny]
    # Every call fans out to Google's tokeninfo endpoint — cap it like login.
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = _get_tokens(user)
        return Response(
            {"user": UserProfileSerializer(user).data, "tokens": tokens},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Profile — GET own profile / PATCH to update
# ---------------------------------------------------------------------------

class ProfileView(SmartDetailView):
    permission_classes = [IsAuthenticated]
    model = User
    detail_serializer = UserProfileSerializer
    edit_serializer = UpdateProfileSerializer
    # Accounts are removed through the deactivate endpoint, never through here.
    deletable = False

    def queryset(self, **kwargs):
        # This route has no pk in the URL, so the lookup must come from the
        # token — never from the (empty) URL kwargs.
        return User.objects.filter(pk=self.request.user.pk)

    def get(self, request, *args, **kwargs):
        data = self.detail_serializer(request.user).data
        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request, **kwargs):
        serializer = self.edit_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(self.detail_serializer(user).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Change Password
# ---------------------------------------------------------------------------

class ChangePasswordView(SmartAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.respond_with("Password updated successfully.")


# ---------------------------------------------------------------------------
# Deactivate Account — owners can deactivate at will
# ---------------------------------------------------------------------------

class DeactivateAccountView(SmartAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeactivateAccountSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.deactivate()

        # Blacklist the refresh token if provided
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        return self.respond_with("Your account has been deactivated.")


# ---------------------------------------------------------------------------
# User List — admin-only listing of all accounts
# ---------------------------------------------------------------------------

class UserListView(SmartPaginationAPIView):
    model = User
    list_serializer = UserListSerializer
    permission_classes = [IsAdminPermission]
