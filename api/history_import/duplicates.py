"""
Best-effort duplicate detection for imported service history records (#103)
— an owner uploading the same invoice twice (or a document that overlaps
with what's already logged) shouldn't end up with the same service/expense
recorded a second time.

For a service: same car + same service_type + date within
DUPLICATE_WINDOW_DAYS of each other is already a strong signal on its own —
e.g. an oil change already logged for 2025 shouldn't get re-added because a
newly-imported document also mentions an oil change from around then, even
if the extracted date/cost aren't identical to what's already stored.

For a part purchase, every import shares the same Expense category
(modification_parts) — "same category, same rough window" alone would flag
unrelated purchases too readily, so this additionally requires the cost or
vendor to actually match.
"""
import datetime

from expenses.models import Expense
from services.models import ServiceRecord
from utils import Constants

DUPLICATE_WINDOW_DAYS = 45


def _parse_date(value):
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def find_duplicate(car, record):
    """Returns the matching existing ServiceRecord/Expense, or None. Never
    raises — a record with an unparseable date just can't be matched."""
    date = _parse_date(record.get("date"))
    if date is None:
        return None

    window = (date - datetime.timedelta(days=DUPLICATE_WINDOW_DAYS), date + datetime.timedelta(days=DUPLICATE_WINDOW_DAYS))

    if record.get("kind") == "part_purchase":
        cost = record.get("cost")
        vendor = (record.get("vendor") or "").strip().lower()
        candidates = Expense.objects.filter(
            car=car, category=Constants.EXPENSE_CATEGORY_PARTS, expense_date__range=window,
        )
        for candidate in candidates:
            candidate_vendor = (candidate.vendor or "").strip().lower()
            cost_matches = cost is not None and candidate.amount is not None and candidate.amount == cost
            vendor_matches = bool(vendor) and vendor == candidate_vendor
            if cost_matches or vendor_matches:
                return candidate
        return None

    service_type = record.get("service_type") or Constants.SERVICE_TYPE_OTHER
    return ServiceRecord.objects.filter(
        car=car, service_type=service_type, service_date__range=window,
    ).first()
