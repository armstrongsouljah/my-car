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
