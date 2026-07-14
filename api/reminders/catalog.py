"""
Static catalog of preset reminder types, used to drive the "Add reminder"
picker on the frontend. Bundled (no DB, no admin editing) — same precedent
as `cars/catalog.py`. Anything not covered here is handled by the frontend's
"Custom reminder" fallback.
"""
from utils import Constants

CATEGORIES = [
    {"key": Constants.REMINDER_CATEGORY_DOCUMENTATION, "label": "Documents"},
    {"key": Constants.REMINDER_CATEGORY_MAINTENANCE, "label": "Maintenance"},
    {"key": Constants.REMINDER_CATEGORY_OTHER, "label": "Other"},
]

CATALOG = [
    # --- Documentation -----------------------------------------------------
    {
        "key": "vehicle_inspection", "title": "Vehicle inspection",
        "category": Constants.REMINDER_CATEGORY_DOCUMENTATION, "is_essential": True,
        "icon": "🔍", "description": "Don't miss the next vehicle inspection date.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 12,
        "suggestion_note": "Inspections are required on a fixed date, regardless of mileage.",
    },
    {
        "key": "car_insurance_renewal", "title": "Car insurance renewal",
        "category": Constants.REMINDER_CATEGORY_DOCUMENTATION, "is_essential": True,
        "icon": "🛡️", "description": "Renew your car insurance before it expires to stay covered.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 12,
        "suggestion_note": "Insurance renews on a fixed date, not mileage.",
    },
    {
        "key": "drivers_license_renewal", "title": "Driver's license renewal",
        "category": Constants.REMINDER_CATEGORY_DOCUMENTATION, "is_essential": False,
        "icon": "🪪", "description": "Renew your drivers license before it expires to stay covered.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 60,
        "suggestion_note": None,
    },
    {
        "key": "driver_medical_check_renewal", "title": "Driver medical check renewal",
        "category": Constants.REMINDER_CATEGORY_DOCUMENTATION, "is_essential": False,
        "icon": "🩺", "description": "Renew your medical documents before they expire to stay covered.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 24,
        "suggestion_note": None,
    },

    # --- Maintenance ---------------------------------------------------------
    {
        "key": "engine_oil_filter_change", "title": "Engine oil & filter change",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": True,
        "icon": "🛢️", "description": "Reduce engine wear and help extend engine life.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
        "default_interval_km": 5000, "default_interval_months": 6,
        "suggestion_note": "Oil changes can be tracked by date and mileage, since they depend on how much you drive.",
    },
    {
        "key": "engine_air_filter_replacement", "title": "Engine air filter replacement",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": True,
        "icon": "🌬️", "description": "Ensure clean airflow for better engine performance.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
        "default_interval_km": 15000, "default_interval_months": 12,
        "suggestion_note": "Engine air filters can be tracked by date and mileage as they wear out with use.",
    },
    {
        "key": "timing_belt_chain_replacement", "title": "Timing belt/chain replacement",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": True,
        "icon": "⚙️", "description": "Avoid serious engine damage from missed timing belt service.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
        "default_interval_km": 100000, "default_interval_months": 60,
        "suggestion_note": None,
    },
    {
        "key": "brake_system_inspection", "title": "Brake system inspection",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": True,
        "icon": "🛑", "description": "Maintain reliable braking and stay safe on the road.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
        "default_interval_km": 20000, "default_interval_months": 12,
        "suggestion_note": None,
    },
    {
        "key": "cabin_air_filter_replacement", "title": "Cabin air filter replacement",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": False,
        "icon": "🌸", "description": "Keep the cabin air clean and comfortable for passengers.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
        "default_interval_km": 15000, "default_interval_months": 12,
        "suggestion_note": None,
    },
    {
        "key": "fuel_filter_replacement", "title": "Fuel filter replacement",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": False,
        "icon": "⛽", "description": "Protect the fuel system and keep the engine running smoothly.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_MILEAGE,
        "default_interval_km": 40000, "default_interval_months": None,
        "suggestion_note": None,
    },
    {
        "key": "serpentine_belt_replacement", "title": "Serpentine belt replacement",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": False,
        "icon": "🔗", "description": "Avoid breakdowns by replacing worn belts in time.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_MILEAGE,
        "default_interval_km": 80000, "default_interval_months": None,
        "suggestion_note": None,
    },
    {
        "key": "spark_plug_replacement", "title": "Spark plug replacement",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": False,
        "icon": "🔥", "description": "Support smooth engine operation and reliable starting.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_MILEAGE,
        "default_interval_km": 30000, "default_interval_months": None,
        "suggestion_note": None,
    },
    {
        "key": "windshield_wiper_blade_replacement", "title": "Windshield wiper blade replacement",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": False,
        "icon": "🌧️", "description": "Keep visibility clear in rain, snow, and dirt.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 12,
        "suggestion_note": None,
    },
    {
        "key": "engine_coolant_change", "title": "Engine coolant change",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": False,
        "icon": "🧊", "description": "Prevent overheating and protect the cooling system.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
        "default_interval_km": 50000, "default_interval_months": 24,
        "suggestion_note": None,
    },
    {
        "key": "battery_inspection", "title": "Battery inspection",
        "category": Constants.REMINDER_CATEGORY_MAINTENANCE, "is_essential": False,
        "icon": "🔋", "description": "Avoid unexpected failures by monitoring battery health.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 6,
        "suggestion_note": None,
    },

    # --- Other -----------------------------------------------------------
    {
        "key": "seasonal_tire_swap", "title": "Seasonal tire swap",
        "category": Constants.REMINDER_CATEGORY_OTHER, "is_essential": False,
        "icon": "🔄", "description": "Improve safety and grip by using the right tires for the season.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 6,
        "suggestion_note": None,
    },
    {
        "key": "ac_system_recharge", "title": "A/C system recharge",
        "category": Constants.REMINDER_CATEGORY_OTHER, "is_essential": False,
        "icon": "❄️", "description": "Maintain effective cooling and system performance.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 24,
        "suggestion_note": None,
    },
    {
        "key": "air_duct_disinfection", "title": "Air duct disinfection",
        "category": Constants.REMINDER_CATEGORY_OTHER, "is_essential": False,
        "icon": "🌀", "description": "Improve air quality and reduce odors inside the cabin.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 12,
        "suggestion_note": None,
    },
    {
        "key": "chemical_car_cleaning", "title": "Chemical car cleaning",
        "category": Constants.REMINDER_CATEGORY_OTHER, "is_essential": False,
        "icon": "🧴", "description": "Refresh and protect your vehicle inside and out.",
        "suggested_method": Constants.REMINDER_TRACKING_METHOD_DATE,
        "default_interval_km": None, "default_interval_months": 6,
        "suggestion_note": None,
    },
]


def get_reminder_catalog():
    return {"categories": CATEGORIES, "items": CATALOG}
