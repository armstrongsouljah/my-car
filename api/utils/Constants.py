# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
PAGINATION_TYPE_PAGE = "page"
PAGINATION_TYPE_CURSOR = "cursor"

# ---------------------------------------------------------------------------
# User roles
# ---------------------------------------------------------------------------
USER_ROLE_ADMIN = "admin"
USER_ROLE_OWNER = "owner"

USER_ROLES = [
    (USER_ROLE_ADMIN, "Admin"),
    (USER_ROLE_OWNER, "Car Owner"),
]

# ---------------------------------------------------------------------------
# Service types
# ---------------------------------------------------------------------------
SERVICE_TYPE_MINOR = "minor_service"
SERVICE_TYPE_MAJOR = "major_service"
SERVICE_TYPE_OIL_CHANGE = "oil_change"
SERVICE_TYPE_BRAKES = "brakes"
SERVICE_TYPE_TYRES = "tyres"
SERVICE_TYPE_BATTERY = "battery"
SERVICE_TYPE_OTHER = "other"

SERVICE_TYPES = [
    (SERVICE_TYPE_MINOR, "Minor Service"),
    (SERVICE_TYPE_MAJOR, "Major Service"),
    (SERVICE_TYPE_OIL_CHANGE, "Oil Change"),
    (SERVICE_TYPE_BRAKES, "Brakes"),
    (SERVICE_TYPE_TYRES, "Tyres"),
    (SERVICE_TYPE_BATTERY, "Battery"),
    (SERVICE_TYPE_OTHER, "Other"),
]

# ---------------------------------------------------------------------------
# Reminder statuses — "whichever comes first" evaluation of km vs months
# ---------------------------------------------------------------------------
REMINDER_STATUS_OK = "ok"
REMINDER_STATUS_DUE_SOON = "due_soon"
REMINDER_STATUS_OVERDUE = "overdue"

REMINDER_DUE_SOON_KM = 500
REMINDER_DUE_SOON_DAYS = 30

# Newly-registered cars have no service/inspection history yet — don't nag
# (dashboard chip or email digest) about that absence until this many days
# after the car was added, giving the owner time to log its history.
REMINDER_NEW_CAR_GRACE_DAYS = 14

# ---------------------------------------------------------------------------
# User-created reminders (catalog-driven or custom)
# ---------------------------------------------------------------------------
REMINDER_CATEGORY_MAINTENANCE = "maintenance"
REMINDER_CATEGORY_DOCUMENTATION = "documentation"
REMINDER_CATEGORY_OTHER = "other"

REMINDER_CATEGORIES = [
    (REMINDER_CATEGORY_MAINTENANCE, "Maintenance"),
    (REMINDER_CATEGORY_DOCUMENTATION, "Documents"),
    (REMINDER_CATEGORY_OTHER, "Other"),
]

REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE = "date_and_mileage"
REMINDER_TRACKING_METHOD_DATE = "date"
REMINDER_TRACKING_METHOD_MILEAGE = "mileage"

REMINDER_TRACKING_METHODS = [
    (REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE, "By date & mileage"),
    (REMINDER_TRACKING_METHOD_DATE, "By date"),
    (REMINDER_TRACKING_METHOD_MILEAGE, "By mileage"),
]

# ---------------------------------------------------------------------------
# Inspection statuses
# ---------------------------------------------------------------------------
INSPECTION_STATUS_PASSED = "passed"
INSPECTION_STATUS_ADVISORIES = "advisories"
INSPECTION_STATUS_FAILED = "failed"

INSPECTION_STATUSES = [
    (INSPECTION_STATUS_PASSED, "Passed"),
    (INSPECTION_STATUS_ADVISORIES, "Passed with Advisories"),
    (INSPECTION_STATUS_FAILED, "Failed"),
]

# Recommended interval between general inspections when the owner has not set one.
INSPECTION_DEFAULT_INTERVAL_MONTHS = 12

# ---------------------------------------------------------------------------
# Expense categories
# ---------------------------------------------------------------------------
EXPENSE_CATEGORY_GARAGE = "garage_visit"
EXPENSE_CATEGORY_PARTS = "modification_parts"
EXPENSE_CATEGORY_FUEL = "fuel"
EXPENSE_CATEGORY_INSURANCE = "insurance"
EXPENSE_CATEGORY_TAX = "tax_licensing"
EXPENSE_CATEGORY_CLEANING = "cleaning"
EXPENSE_CATEGORY_OTHER = "other"

EXPENSE_CATEGORIES = [
    (EXPENSE_CATEGORY_GARAGE, "Garage Visit"),
    (EXPENSE_CATEGORY_PARTS, "Modification / Parts"),
    (EXPENSE_CATEGORY_FUEL, "Fuel"),
    (EXPENSE_CATEGORY_INSURANCE, "Insurance"),
    (EXPENSE_CATEGORY_TAX, "Tax & Licensing"),
    (EXPENSE_CATEGORY_CLEANING, "Cleaning & Detailing"),
    (EXPENSE_CATEGORY_OTHER, "Other"),
]

# ---------------------------------------------------------------------------
# Mileage update reminder frequencies (account-level setting)
# ---------------------------------------------------------------------------
MILEAGE_REMINDER_OFF = "off"
MILEAGE_REMINDER_DAILY = "daily"
MILEAGE_REMINDER_WEEKLY = "weekly"
MILEAGE_REMINDER_MONTHLY = "monthly"

MILEAGE_REMINDER_FREQUENCIES = [
    (MILEAGE_REMINDER_OFF, "Off"),
    (MILEAGE_REMINDER_DAILY, "Daily"),
    (MILEAGE_REMINDER_WEEKLY, "Weekly"),
    (MILEAGE_REMINDER_MONTHLY, "Monthly"),
]

MILEAGE_REMINDER_INTERVAL_DAYS = {
    MILEAGE_REMINDER_DAILY: 1,
    MILEAGE_REMINDER_WEEKLY: 7,
    MILEAGE_REMINDER_MONTHLY: 30,
}

# ---------------------------------------------------------------------------
# Account deactivation → deletion grace period
# ---------------------------------------------------------------------------
# A deactivated account can be reactivated by support within this window;
# past it, the daily purge sweep (tasks.purge_deactivated_accounts_task)
# permanently deletes the account and everything that cascades from it.
# The "30 days" figure is also hardcoded in frontend copy (Settings' Danger
# zone section + confirm dialog, and the /privacy page) — update those too
# if this changes.
ACCOUNT_DELETION_GRACE_DAYS = 30

# How long after deactivation the daily reminder sweep
# (tasks.send_account_deletion_reminder_task) emails the owner that deletion
# is coming, so they still have ACCOUNT_DELETION_GRACE_DAYS - this figure
# days of runway to contact support if they want to reactivate.
ACCOUNT_DELETION_REMINDER_DAYS = 15

# ---------------------------------------------------------------------------
# Unverified signup → nudge/purge lifecycle
# ---------------------------------------------------------------------------
# RegisterView creates the User row (is_active=True) and sends an OTP before
# the address is confirmed as real. If it's never verified, nothing about the
# row changes on its own, so a daily sweep drives the rest of the lifecycle:
#
# Day EMAIL_VERIFY_REMINDER_DAYS after signup: still-unverified accounts get
# a nudge email with a fresh OTP (tasks.send_email_verification_reminder_task).
# Day EMAIL_VERIFY_PURGE_DAYS after signup: still-unverified accounts are
# deleted outright (tasks.purge_unverified_accounts_task) — unlike the
# deactivation-to-deletion lifecycle above, there's no reactivate path; the
# account was never confirmed as real to begin with. See #23.
EMAIL_VERIFY_REMINDER_DAYS = 7
EMAIL_VERIFY_PURGE_DAYS = 15

# ---------------------------------------------------------------------------
# Reminder claim lease (mileage, deletion, and email-verification reminders)
# ---------------------------------------------------------------------------
# The daily sweeps for each reminder type claim a user (via a *_queued_at
# timestamp) before dispatching the actual send as its own task, so one
# user's send failure can't crash the rest of that day's batch. If the send
# never confirms (worker crash, lost task, an exception in the send itself),
# the claim goes stale after this many hours and the next sweep reclaims and
# retries it. Comfortably longer than how long a single send attempt could
# plausibly take, short enough that a genuinely stuck claim gets retried
# same-day rather than waiting a full 24h for the next scheduled run.
REMINDER_CLAIM_LEASE_HOURS = 6

# ---------------------------------------------------------------------------
# Fuel types
# ---------------------------------------------------------------------------
FUEL_TYPE_PETROL = "petrol"
FUEL_TYPE_DIESEL = "diesel"
FUEL_TYPE_HYBRID = "hybrid"
FUEL_TYPE_ELECTRIC = "electric"

FUEL_TYPES = [
    (FUEL_TYPE_PETROL, "Petrol"),
    (FUEL_TYPE_DIESEL, "Diesel"),
    (FUEL_TYPE_HYBRID, "Hybrid"),
    (FUEL_TYPE_ELECTRIC, "Electric"),
]

# ---------------------------------------------------------------------------
# AI assistant — chat message roles
# ---------------------------------------------------------------------------
# "user" and "model" mirror Gemini's own role names so history maps 1:1 onto
# the provider's `contents`. "tool" rows record a tool call + its result for
# transparency and are not replayed as conversational turns.
ASSISTANT_ROLE_USER = "user"
ASSISTANT_ROLE_MODEL = "model"
ASSISTANT_ROLE_TOOL = "tool"

ASSISTANT_ROLES = [
    (ASSISTANT_ROLE_USER, "User"),
    (ASSISTANT_ROLE_MODEL, "Assistant"),
    (ASSISTANT_ROLE_TOOL, "Tool"),
]

# ---------------------------------------------------------------------------
# Support — contact-us subjects
# ---------------------------------------------------------------------------
SUPPORT_SUBJECT_GENERAL_ACCOUNT = "general_account"
SUPPORT_SUBJECT_APP_INQUIRY = "app_inquiry"
SUPPORT_SUBJECT_FEATURE_SUGGESTION = "feature_suggestion"
SUPPORT_SUBJECT_OTHER = "other"

SUPPORT_SUBJECTS = [
    (SUPPORT_SUBJECT_GENERAL_ACCOUNT, "General Account"),
    (SUPPORT_SUBJECT_APP_INQUIRY, "App Inquiry"),
    (SUPPORT_SUBJECT_FEATURE_SUGGESTION, "Feature Suggestions"),
    (SUPPORT_SUBJECT_OTHER, "Other"),
]

SUPPORT_MAX_ATTACHMENTS = 5
SUPPORT_MAX_ATTACHMENT_SIZE_MB = 10
# Attachments are never written to disk — they ride along on the notification
# email and are then dropped. That means the whole batch is base64-encoded into
# the Celery message, so the combined size needs its own (smaller) ceiling.
SUPPORT_MAX_ATTACHMENT_TOTAL_MB = 10

# ---------------------------------------------------------------------------
# Upload types
# ---------------------------------------------------------------------------
# Support attachments and inspection reports are screenshots, photos and
# scanned documents. Anything else gets rejected rather than mailed on to the
# support inbox or parked in storage.
ALLOWED_UPLOAD_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".pdf")
ALLOWED_UPLOAD_CONTENT_TYPES = (
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/pdf",
)
# Inspection reports had no size cap at all (unlike support attachments,
# see SUPPORT_MAX_ATTACHMENT_SIZE_MB above) -- same 10MB ceiling for
# consistency.
INSPECTION_REPORT_MAX_SIZE_MB = 10

# ---------------------------------------------------------------------------
# Email verification OTP
# ---------------------------------------------------------------------------
# Wrong guesses allowed against a single code before it is burned and the owner
# has to request a new one.
OTP_MAX_FAILED_ATTEMPTS = 5

# ---------------------------------------------------------------------------
# Country / currency (see #40)
# ---------------------------------------------------------------------------
# Not exhaustive — just the countries/currencies the app has users in today
# plus the Eurozone. A country missing from COUNTRY_CHOICES/CURRENCY_TO_COUNTRY
# just leaves `currency` unset at signup, same as today's "no currency"
# fallback, rather than guessing.
COUNTRY_CHOICES = [
    ("", "Prefer not to say"),
    ("AT", "Austria"),
    ("AU", "Australia"),
    ("AE", "United Arab Emirates"),
    ("BE", "Belgium"),
    ("CA", "Canada"),
    ("DE", "Germany"),
    ("EG", "Egypt"),
    ("ES", "Spain"),
    ("FI", "Finland"),
    ("FR", "France"),
    ("GB", "United Kingdom"),
    ("GH", "Ghana"),
    ("IE", "Ireland"),
    ("IN", "India"),
    ("IT", "Italy"),
    ("KE", "Kenya"),
    ("NG", "Nigeria"),
    ("NL", "Netherlands"),
    ("PT", "Portugal"),
    ("RW", "Rwanda"),
    ("TZ", "Tanzania"),
    ("UG", "Uganda"),
    ("US", "United States"),
    ("ZA", "South Africa"),
]

# ISO 3166-1 alpha-2 country -> default ISO 4217 currency, used to seed
# `User.currency` at signup from `User.country`.
COUNTRY_TO_CURRENCY = {
    "UG": "UGX", "KE": "KES", "TZ": "TZS", "RW": "RWF",
    "NG": "NGN", "GH": "GHS", "ZA": "ZAR", "EG": "EGP",
    "US": "USD", "GB": "GBP", "IN": "INR", "AE": "AED",
    "CA": "CAD", "AU": "AUD",
    # Eurozone
    "DE": "EUR", "FR": "EUR", "ES": "EUR", "IT": "EUR", "NL": "EUR",
    "IE": "EUR", "PT": "EUR", "BE": "EUR", "AT": "EUR", "FI": "EUR",
}

CURRENCY_CHOICES = [
    ("", "Not set — show plain amounts"),
    ("UGX", "Ugandan Shilling (UGX)"),
    ("KES", "Kenyan Shilling (KES)"),
    ("TZS", "Tanzanian Shilling (TZS)"),
    ("RWF", "Rwandan Franc (RWF)"),
    ("NGN", "Nigerian Naira (NGN)"),
    ("GHS", "Ghanaian Cedi (GHS)"),
    ("ZAR", "South African Rand (ZAR)"),
    ("EGP", "Egyptian Pound (EGP)"),
    ("USD", "US Dollar (USD)"),
    ("GBP", "British Pound (GBP)"),
    ("EUR", "Euro (EUR)"),
    ("INR", "Indian Rupee (INR)"),
    ("AED", "UAE Dirham (AED)"),
    ("CAD", "Canadian Dollar (CAD)"),
    ("AUD", "Australian Dollar (AUD)"),
]
