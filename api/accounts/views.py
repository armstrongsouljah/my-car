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


# ---------------------------------------------------------------------------
# Register — creates account, sends OTP; no tokens until verified
# ---------------------------------------------------------------------------

class RegisterView(SmartAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _dispatch_otp(user)
        return self.respond_with(
            f"Account created. A verification code has been sent to {user.email}.",
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
        _dispatch_otp(user)
        return self.respond_with(
            f"A new verification code has been sent to {user.email}."
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
