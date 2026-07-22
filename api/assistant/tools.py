"""
Assistant tools — the functions the LLM may call to ground its answers in the
owner's real data (and a couple of external automotive sources).

Each tool takes a ``ToolContext`` (the pinned car + its owner) plus whatever
arguments the model supplies, and returns a JSON-serialisable dict. The
registry below is provider-agnostic; ``assistant/gemini.py`` adapts
``FUNCTION_DECLARATIONS`` into Gemini's schema and dispatches through
``execute_tool``.

Vehicle context, service history, maintenance status and expenses come
straight from models we already own. VIN decoding hits the free NHTSA vPIC
API. DTC and part lookups are stubbed — they need licensed automotive data —
but the tool surface is in place so wiring a real provider later is a drop-in.
"""
from dataclasses import dataclass
from decimal import Decimal

import requests
from django.db.models import Sum

from utils import Constants

from cars.models import Car
from services.models import ServiceRecord
from services.reminders import build_inspection_reminder, build_service_reminder
from expenses.models import Expense
from reminders.models import Reminder


@dataclass
class ToolContext:
    car: Car
    owner_id: int


# ---------------------------------------------------------------------------
# Owner-data tools — grounded in models we already store.
# ---------------------------------------------------------------------------
def get_vehicle_details(context):
    """The pinned car's spec — the anchor for every other answer."""
    car = context.car
    return {
        "make": car.make,
        "model": car.model,
        "year": car.year,
        "vin": car.vin or None,
        "registration_number": car.registration_number or None,
        "fuel_type": car.get_fuel_type_display(),
        "color": car.color or None,
        "current_odometer_km": car.current_odometer_km,
    }


def get_service_history(context, limit=5):
    """Most recent logged services for the car."""
    limit = max(1, min(int(limit or 5), 20))
    records = ServiceRecord.objects.filter(car=context.car).order_by("-service_date", "-created_at")[:limit]
    return {
        "count": len(records),
        "services": [
            {
                "type": r.get_service_type_display(),
                "date": r.service_date.isoformat(),
                "odometer_km": r.odometer_km,
                "garage": r.garage_name or None,
                "cost": str(r.cost) if r.cost is not None else None,
                "description": r.description or None,
            }
            for r in records
        ],
    }


def get_maintenance_status(context):
    """
    What's due for the car — the next-service and general-inspection reminders
    (reusing the existing reminder engine) plus any owner-configured reminders.
    """
    car = context.car
    custom = []
    for reminder in Reminder.objects.filter(car=car):
        custom.append(
            {
                "title": reminder.title,
                "category": reminder.get_category_display(),
                "next_due_date": reminder.next_due_date.isoformat() if reminder.next_due_date else None,
                "next_due_odometer_km": reminder.next_due_odometer_km,
            }
        )
    return {
        "service": build_service_reminder(car),
        "inspection": build_inspection_reminder(car),
        "custom_reminders": custom,
    }


def get_expense_summary(context):
    """Total spend on the car, broken down by category."""
    rows = (
        Expense.objects.filter(car=context.car)
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    labels = dict(Constants.EXPENSE_CATEGORIES)
    # SQLite's Sum() drops trailing zeros on DecimalField (e.g. Decimal("120")
    # instead of Decimal("120.00")); quantize explicitly so formatting is
    # consistent across backends.
    by_category = [
        {"category": labels.get(r["category"], r["category"]), "total": _format_money(r["total"])} for r in rows
    ]
    grand_total = sum((r["total"] for r in rows), start=Decimal("0"))
    return {"total": _format_money(grand_total), "by_category": by_category}


def _format_money(value):
    return str(value.quantize(Decimal("0.01")))


# ---------------------------------------------------------------------------
# External automotive tools.
# ---------------------------------------------------------------------------
def decode_vin(context, vin=None):
    """
    Decode a VIN via NHTSA vPIC (free, no key). Defaults to the pinned car's
    VIN. Returns the decoded make/model/year/engine so answers can be precise
    even when the owner never filled in those fields.
    """
    vin = (vin or context.car.vin or "").strip()
    if not vin:
        return {"error": "No VIN available for this car. Ask the owner to add one."}
    try:
        resp = requests.get(
            f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json",
            timeout=8,
        )
        resp.raise_for_status()
        row = (resp.json().get("Results") or [{}])[0]
    except (requests.RequestException, ValueError) as exc:
        return {"error": f"VIN decode service unavailable: {exc}"}
    keep = ("Make", "Model", "ModelYear", "Trim", "EngineModel", "DisplacementL", "FuelTypePrimary", "BodyClass")
    decoded = {k: row.get(k) for k in keep if row.get(k)}
    return {"vin": vin, "decoded": decoded or {"note": "vPIC returned no fields for this VIN."}}


# Minimal seed of common generic OBD-II codes. The full SAE set is public and
# would be loaded from a table; manufacturer-specific codes need licensed data.
_GENERIC_DTC = {
    "P0300": "Random/multiple cylinder misfire detected.",
    "P0301": "Cylinder 1 misfire detected.",
    "P0420": "Catalyst system efficiency below threshold (bank 1).",
    "P0442": "Evaporative emission system leak detected (small leak).",
    "P0455": "Evaporative emission system leak detected (large leak).",
    "P0171": "System too lean (bank 1).",
    "P0128": "Coolant thermostat below regulating temperature.",
}


def lookup_dtc(context, code):
    """Explain an OBD-II diagnostic trouble code (generic codes only for now)."""
    code = (code or "").strip().upper()
    meaning = _GENERIC_DTC.get(code)
    if meaning:
        return {"code": code, "meaning": meaning, "scope": "generic"}
    return {
        "code": code,
        "meaning": None,
        "note": (
            "Not in the generic seed set. Manufacturer-specific codes and the "
            "full SAE table require a licensed diagnostics data source (not yet "
            "connected)."
        ),
    }


def find_part(context, component):
    """Look up a part number for a component (stub — needs a parts catalog)."""
    return {
        "component": component,
        "part_number": None,
        "note": (
            "Parts catalog not yet connected. This needs a licensed parts data "
            "provider keyed by the vehicle's year/make/model/engine."
        ),
    }


# ---------------------------------------------------------------------------
# Registry + Gemini function declarations.
# ---------------------------------------------------------------------------
TOOL_REGISTRY = {
    "get_vehicle_details": get_vehicle_details,
    "get_service_history": get_service_history,
    "get_maintenance_status": get_maintenance_status,
    "get_expense_summary": get_expense_summary,
    "decode_vin": decode_vin,
    "lookup_dtc": lookup_dtc,
    "find_part": find_part,
}

FUNCTION_DECLARATIONS = [
    {
        "name": "get_vehicle_details",
        "description": "Get the make, model, year, VIN, fuel type and current odometer of the car this chat is about. Call this first when you need vehicle context.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_service_history",
        "description": "List the car's most recent logged services (type, date, odometer, garage, cost).",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "How many recent services to return (1-20, default 5)."}},
        },
    },
    {
        "name": "get_maintenance_status",
        "description": "Get what maintenance is due or overdue for the car: next service, general inspection, and any owner-configured reminders.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_expense_summary",
        "description": "Get total spend on the car broken down by expense category.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "decode_vin",
        "description": "Decode a VIN into make/model/year/engine using the NHTSA database. Defaults to this car's VIN if none is given.",
        "parameters": {
            "type": "object",
            "properties": {"vin": {"type": "string", "description": "17-character VIN. Optional; defaults to the car's stored VIN."}},
        },
    },
    {
        "name": "lookup_dtc",
        "description": "Explain an OBD-II diagnostic trouble code (e.g. P0420).",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "The trouble code, e.g. 'P0420'."}},
            "required": ["code"],
        },
    },
    {
        "name": "find_part",
        "description": "Find a part number for a component on this vehicle (e.g. 'cabin air filter').",
        "parameters": {
            "type": "object",
            "properties": {"component": {"type": "string", "description": "The component to find a part for."}},
            "required": ["component"],
        },
    },
]


def execute_tool(name, args, context):
    """Dispatch a tool call by name. Unknown tools return a structured error."""
    func = TOOL_REGISTRY.get(name)
    if func is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(context, **(args or {}))
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}
