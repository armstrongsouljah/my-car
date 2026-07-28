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
# The "60 days" figure is also hardcoded in frontend copy (Settings' Danger
# zone section + confirm dialog, and the /privacy page) — update those too
# if this changes.
ACCOUNT_DELETION_GRACE_DAYS = 60

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

# ---------------------------------------------------------------------------
# Email verification OTP
# ---------------------------------------------------------------------------
# Wrong guesses allowed against a single code before it is burned and the owner
# has to request a new one.
OTP_MAX_FAILED_ATTEMPTS = 5
