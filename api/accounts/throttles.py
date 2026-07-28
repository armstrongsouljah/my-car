"""
Throttles for the unauthenticated auth endpoints.

These are all `AllowAny` and all of them are cheap to script against, so each
one gets its own scope rather than sharing the global `anon` bucket — a bot
grinding the login form shouldn't eat the budget a real visitor needs to
register.

The OTP throttles key on the *target email* rather than the caller's IP:
capping guesses per account is what actually stops a brute force, since an
attacker with a pool of IPs would otherwise walk straight around an IP-keyed
limit. `EmailVerificationOTP.register_failed_attempt()` is the hard backstop —
this is the cheap first line that keeps the load off the database.
"""
from rest_framework.throttling import SimpleRateThrottle


class BaseAuthThrottle(SimpleRateThrottle):
    """Rate-limits by client IP, for both anonymous and authenticated callers."""

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class LoginRateThrottle(BaseAuthThrottle):
    scope = "auth_login"


class RegisterRateThrottle(BaseAuthThrottle):
    scope = "auth_register"


class EmailScopedThrottle(SimpleRateThrottle):
    """Rate-limits per email address in the request body, falling back to IP."""

    def get_cache_key(self, request, view):
        try:
            email = (request.data or {}).get("email")
        except Exception:  # noqa: BLE001 — unparseable body, fall back to IP
            email = None
        ident = email.strip().lower() if isinstance(email, str) and email.strip() else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class VerifyOTPRateThrottle(EmailScopedThrottle):
    scope = "auth_verify_otp"


class ResendOTPRateThrottle(EmailScopedThrottle):
    scope = "auth_resend_otp"
