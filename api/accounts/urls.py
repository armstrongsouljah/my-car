from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import (
    RegisterView,
    VerifyEmailView,
    ResendOTPView,
    LoginView,
    LogoutView,
    ProfileView,
    ChangePasswordView,
    GoogleAuthView,
    DeactivateAccountView,
    UserListView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-otp/", ResendOTPView.as_view(), name="auth-resend-otp"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("google/", GoogleAuthView.as_view(), name="auth-google"),
    path("profile/", ProfileView.as_view(), name="auth-profile"),
    path("password/change/", ChangePasswordView.as_view(), name="auth-password-change"),
    path("account/deactivate/", DeactivateAccountView.as_view(), name="auth-deactivate"),
    path("users/", UserListView.as_view(), name="auth-users"),
]
