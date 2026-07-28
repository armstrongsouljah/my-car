import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("REDIS_URL", "locmem")
os.environ.setdefault("DEFAULT_FROM_EMAIL", "support@glavbox.com")

from .settings import *  # noqa: E402,F401,F403

DEBUG = False

# The test client talks plain HTTP and never sets X-Forwarded-Proto, so the
# transport-security defaults in settings.py (which key off `not DEBUG`, not
# the DEBUG reassignment above since they're computed at import time) would
# otherwise 301-redirect every single request to itself over HTTPS.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Throttle counters live in the cache and leak between tests, so leaving the
# broad scopes on would make the suite order-dependent. The per-endpoint scopes
# that already have their own tests (support_request, assistant_chat) keep their
# real rates; the rest are off, and the tests that exercise them set their own
# rate (see `throttled_rates` in accounts/tests.py).
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],  # noqa: F405
        "anon": None,
        "user": None,
        "auth_login": None,
        "auth_register": None,
        "auth_verify_otp": None,
        "auth_resend_otp": None,
        "auth_password_reset_request": None,
        "auth_password_reset_confirm": None,
    },
}
