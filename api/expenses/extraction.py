"""
Turns a photographed/screenshotted receipt or invoice into a proposed set of
Expense field values -- see #87. The image is only ever read into memory to
send to Gemini (see #33's no-local-disk-uploads convention) and is never
stored -- extraction is a one-shot, scratch input, not an attachment kept on
the saved expense.

Only fields Gemini is actually confident about come back at all -- nothing
in RESPONSE_SCHEMA is marked "required", and the prompt tells the model to
omit anything illegible rather than guess, so the owner fills in the rest
by hand instead of getting a wrong-looking prefill.
"""
import json

from django.conf import settings

from utils import Constants

_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".pdf": "application/pdf",
}

_CATEGORY_CHOICES = [code for code, _label in Constants.EXPENSE_CATEGORIES]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": _CATEGORY_CHOICES,
            "description": "Best matching expense category for this receipt/invoice.",
        },
        "amount": {"type": "number", "description": "Total amount charged, numeric only, no currency symbol"},
        "expense_date": {"type": "string", "description": "YYYY-MM-DD"},
        "vendor": {"type": "string", "description": "Garage, shop, or station name"},
        "description": {"type": "string", "description": "Brief note of what this was for"},
        "odometer_km": {"type": "integer", "description": "Only if actually printed/written on the receipt"},
        "litres": {"type": "number", "description": "Fuel purchases only"},
    },
}

EXTRACTION_PROMPT = (
    "This image is a photo or screenshot of a car-related receipt, invoice, or "
    "handwritten service note -- it may be handwritten, not just printed. Extract "
    "whatever you can confidently read: the expense category (fuel, garage_visit "
    "for labor/service, modification_parts for buying parts, insurance, "
    "tax_licensing, cleaning, or other), the total amount charged, the date, the "
    "vendor/garage/station name, a brief description of what it was for, the "
    "odometer reading if it's actually printed or written down, and litres if "
    "this is a fuel purchase. Omit any field you can't confidently read rather "
    "than guessing -- a missing field is far better than a wrong one. If nothing "
    "in the image resembles a receipt, invoice, or service note at all, return "
    "an empty object."
)


class ExtractionError(Exception):
    """Raised when the image can't be turned into anything usable at all --
    unsupported file type, or the model call itself failed."""


def extract_expense(uploaded_file):
    """
    :param uploaded_file: a Django UploadedFile (image or PDF).
    :returns: dict with category, amount, expense_date, vendor, description,
        odometer_km, litres -- any field Gemini wasn't confident about is
        None rather than a guess.
    :raises ExtractionError: unsupported type, not configured, or the model
        call/response failed outright.
    """
    from google.genai import types

    mime_type = _mime_type_of(uploaded_file)
    part = types.Part.from_bytes(data=uploaded_file.read(), mime_type=mime_type)
    raw = _call_gemini(part)
    return _normalize(raw)


def _mime_type_of(uploaded_file):
    name = (uploaded_file.name or "").lower()
    for ext, mime_type in _MIME_TYPES.items():
        if name.endswith(ext):
            return mime_type
    content_type = getattr(uploaded_file, "content_type", None)
    if content_type in Constants.ALLOWED_UPLOAD_CONTENT_TYPES:
        return content_type
    raise ExtractionError("Unsupported file type -- upload a photo or PDF of the receipt.")


def _call_gemini(part):
    from google import genai
    from google.genai import types

    if not settings.GEMINI_API_KEY:
        raise ExtractionError("Receipt scanning isn't configured on this server.")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=EXTRACTION_PROMPT,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
        temperature=0.1,
    )
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL, contents=[part], config=config,
        )
        data = json.loads(response.text)
    except ExtractionError:
        raise
    except Exception as err:
        raise ExtractionError("Couldn't read that receipt. Please try again.") from err

    return data if isinstance(data, dict) else {}


def _normalize(raw):
    category = raw.get("category")
    if category not in _CATEGORY_CHOICES:
        category = None

    amount = raw.get("amount")
    litres = raw.get("litres")
    odometer_km = raw.get("odometer_km")
    return {
        "category": category,
        "amount": amount if isinstance(amount, (int, float)) else None,
        "expense_date": raw.get("expense_date") or None,
        "vendor": (raw.get("vendor") or "").strip(),
        "description": (raw.get("description") or "").strip(),
        "odometer_km": odometer_km if isinstance(odometer_km, (int, float)) else None,
        "litres": litres if isinstance(litres, (int, float)) else None,
    }
