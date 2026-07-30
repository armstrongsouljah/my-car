from datetime import timedelta
from pathlib import Path

import dj_database_url
from celery.schedules import crontab
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")

# Defaults to False: a missing/misspelled DEBUG in a deployed environment must
# fail closed, not serve tracebacks and settings values to the internet.
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# The GKE ingress (GCLB) terminates TLS at the edge and forwards plain HTTP to
# the container, so Django must be told to trust X-Forwarded-Proto to know a
# request was actually HTTPS (otherwise CSRF's Origin check rejects same-origin
# admin logins).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# ---------------------------------------------------------------------------
# Transport security
# ---------------------------------------------------------------------------
# All default to "on unless DEBUG", so local HTTP development keeps working
# while any deployed environment is hardened without needing extra env vars.
#
# The Gateway already redirects HTTP->HTTPS at the edge; SECURE_SSL_REDIRECT is
# the backstop for anything that reaches the pod over plain HTTP anyway, and it
# reads the proxy header set above to avoid a redirect loop.
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=not DEBUG, cast=bool)
# Kubernetes probes hit the pod directly over HTTP and must not be redirected.
SECURE_REDIRECT_EXEMPT = [r"^health/$"]

SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=not DEBUG, cast=bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# One year. Without HSTS the very first request of a session can still be
# downgraded to HTTP before the redirect fires.
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG, cast=bool)
# Preload is deliberately opt-in: submitting to the browser preload list is
# hard to reverse, so it should be a conscious decision rather than a default.
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)

# Base URL of the my-car frontend, used to build public-facing links in
# emails (verification, password reset, the monthly expense report, etc.).
# Only defaults to localhost in DEBUG — same fail-closed reasoning as
# SECRET_KEY/DATABASE_URL/DEFAULT_FROM_EMAIL above: a deployed environment
# that forgets to set this must refuse to start, not silently mail out
# http://localhost:3000 links nobody outside the container can open.
FRONTEND_URL = (config("FRONTEND_URL", default="http://localhost:3000") if DEBUG else config("FRONTEND_URL")).rstrip(
    "/"
)

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_celery_results",
]

LOCAL_APPS = [
    "accounts",
    "cars",
    "services",
    "inspections",
    "expenses",
    "reminders",
    "assistant",
    "support",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Redis cache — car information is cached here (see utils/Cache.py)
# ---------------------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/1")

if REDIS_URL == "locmem":
    # Build-time / test escape hatch: no Redis available.
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                # Cache is a read-through optimization, not a hard dependency —
                # a Redis blip should degrade to uncached responses, not 500s.
                "IGNORE_EXCEPTIONS": True,
            },
            "KEY_PREFIX": "mycar",
        }
    }

# Cars change rarely — Cache.invalidate_owner()/invalidate_car() bust this on
# every create/update/delete, so a long TTL is safe and just cuts DB load for
# untouched cars in between.
CAR_CACHE_TTL_SECONDS = config("CAR_CACHE_TTL_SECONDS", default=86400, cast=int)

# ---------------------------------------------------------------------------
# DRF / JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # A baseline ceiling on every route. Individual views layer tighter,
    # purpose-built scopes on top (see DEFAULT_THROTTLE_RATES below).
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("ANON_THROTTLE", default="60/min"),
        "user": config("USER_THROTTLE", default="240/min"),
        # Caps AI assistant message sends per user — each one costs LLM tokens.
        "assistant_chat": config("ASSISTANT_CHAT_THROTTLE", default="30/min"),
        # The contact form is AllowAny (visitors included) — cap submissions
        # per user/IP so bots can't flood the support inbox or storage.
        "support_request": config("SUPPORT_REQUEST_THROTTLE", default="5/hour"),
        # Auth endpoints are AllowAny and cheap to script against. Login and
        # register key on IP; the OTP scopes key on the target email so a
        # distributed attacker can't grind one account from many addresses.
        "auth_login": config("AUTH_LOGIN_THROTTLE", default="10/min"),
        "auth_register": config("AUTH_REGISTER_THROTTLE", default="10/hour"),
        "auth_verify_otp": config("AUTH_VERIFY_OTP_THROTTLE", default="10/hour"),
        "auth_resend_otp": config("AUTH_RESEND_OTP_THROTTLE", default="5/hour"),
        "auth_password_reset_request": config("AUTH_PASSWORD_RESET_REQUEST_THROTTLE", default="5/hour"),
        "auth_password_reset_confirm": config("AUTH_PASSWORD_RESET_CONFIRM_THROTTLE", default="10/hour"),
    },
    # Client IP is read from X-Forwarded-For, which the caller can spoof unless
    # we know how many proxies sit in front of us. Behind the GKE Gateway the
    # header is "<client>, <gclb>", so NUM_PROXIES=2 picks the real client.
    # Left unset for local runs, where there is no proxy at all.
    "NUM_PROXIES": config("NUM_PROXIES", default=None, cast=lambda v: int(v) if v not in (None, "") else None),
}

# ---------------------------------------------------------------------------
# AI assistant (Gemini)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = config("GEMINI_API_KEY", default="")
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-3.6-flash")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_MINUTES", default=60, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_DAYS", default=7, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:3000", cast=Csv())
CORS_ALLOW_CREDENTIALS = True

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth integrations
# ---------------------------------------------------------------------------
GOOGLE_OAUTH_CLIENT_ID = config("GOOGLE_OAUTH_CLIENT_ID", default="")

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")

OTP_EXPIRY_MINUTES = config("OTP_EXPIRY_MINUTES", default=10, cast=int)

# ---------------------------------------------------------------------------
# Cloudinary (server-side) — standard cloudinary://<key>:<secret>@<cloud_name>
# form, separate from the frontend's public NEXT_PUBLIC_CLOUDINARY_* build
# args used for unsigned browser uploads. Only needed so the account-purge
# sweep can delete a deleted owner's car photos; left blank,
# utils.Cloudinary.delete_photos() just skips cleanup.
# ---------------------------------------------------------------------------
CLOUDINARY_URL = config("CLOUDINARY_URL", default="")

# ---------------------------------------------------------------------------
# Seeded super admin
# ---------------------------------------------------------------------------
ADMIN_EMAIL = config("ADMIN_EMAIL", default="admin@mycar.com")
ADMIN_PASSWORD = config("ADMIN_PASSWORD", default="")

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
import ssl as _ssl

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="django-db")
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

if CELERY_BROKER_URL.startswith("rediss://"):
    # Verify the broker's certificate. CERT_NONE encrypts the connection but
    # accepts any certificate, which leaves it open to an undetected MITM —
    # the encryption is then only as good as the network you're trusting.
    # CELERY_BROKER_SSL_CA_CERTS points at a CA bundle when the broker uses a
    # private CA (Memorystore does; leave unset for a publicly-trusted cert).
    _ssl_opts = {"ssl_cert_reqs": _ssl.CERT_REQUIRED}
    _ssl_ca_certs = config("CELERY_BROKER_SSL_CA_CERTS", default="")
    if _ssl_ca_certs:
        _ssl_opts["ssl_ca_certs"] = _ssl_ca_certs
    CELERY_BROKER_USE_SSL = _ssl_opts
    CELERY_REDIS_BACKEND_USE_SSL = _ssl_opts

# Daily reminder sweep — emails owners whose cars are due (or soon due) for
# service or a general inspection.
CELERY_BEAT_SCHEDULE = {
    "send-service-reminders": {
        "task": "tasks.send_due_reminders_task",
        "schedule": 60 * 60 * 24,  # once a day
    },
    "send-mileage-reminders": {
        "task": "tasks.send_mileage_reminders_task",
        "schedule": 60 * 60 * 24,  # once a day; per-user cadence applied inside
    },
    "purge-deactivated-accounts": {
        "task": "tasks.purge_deactivated_accounts_task",
        "schedule": 60 * 60 * 24,  # once a day
    },
    "send-account-deletion-reminders": {
        "task": "tasks.send_account_deletion_reminder_task",
        "schedule": 60 * 60 * 24,  # once a day
    },
    "send-email-verification-reminders": {
        "task": "tasks.send_email_verification_reminder_task",
        "schedule": 60 * 60 * 24,  # once a day
    },
    "purge-unverified-accounts": {
        "task": "tasks.purge_unverified_accounts_task",
        "schedule": 60 * 60 * 24,  # once a day
    },
    "send-monthly-expense-reports": {
        "task": "tasks.send_monthly_expense_reports_task",
        "schedule": crontab(day_of_month=1, hour=6, minute=0),  # once, on the 1st of each month
    },
    "refresh-exchange-rates": {
        "task": "tasks.refresh_exchange_rates_task",
        "schedule": crontab(hour=5, minute=0),  # once a day, ahead of the monthly report sweep above
    },
}
