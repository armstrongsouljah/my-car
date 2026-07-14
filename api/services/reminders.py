"""
Reminder engine — evaluates "whichever comes first" service intervals and
general inspection recency for a car.

Status semantics:
- overdue:  the km threshold has been passed OR the date has passed.
- due_soon: within REMINDER_DUE_SOON_KM km or REMINDER_DUE_SOON_DAYS days
            of either threshold.
- ok:       neither threshold is near.
"""
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from utils import Constants


def _service_status(car, record, today):
    """Evaluate a service record's interval rule against the car's current state."""
    statuses = []

    if record.next_due_odometer_km is not None:
        km_remaining = record.next_due_odometer_km - car.current_odometer_km
        if km_remaining <= 0:
            statuses.append((Constants.REMINDER_STATUS_OVERDUE, f"service was due {abs(km_remaining)} km ago"))
        elif km_remaining <= Constants.REMINDER_DUE_SOON_KM:
            statuses.append((Constants.REMINDER_STATUS_DUE_SOON, f"service due in {km_remaining} km"))

    if record.next_due_date is not None:
        days_remaining = (record.next_due_date - today).days
        if days_remaining <= 0:
            statuses.append((Constants.REMINDER_STATUS_OVERDUE, f"service was due on {record.next_due_date.isoformat()}"))
        elif days_remaining <= Constants.REMINDER_DUE_SOON_DAYS:
            statuses.append((Constants.REMINDER_STATUS_DUE_SOON, f"service due on {record.next_due_date.isoformat()}"))

    # Whichever comes first: overdue beats due_soon beats ok.
    for status in (Constants.REMINDER_STATUS_OVERDUE, Constants.REMINDER_STATUS_DUE_SOON):
        for s, reason in statuses:
            if s == status:
                return s, reason

    return Constants.REMINDER_STATUS_OK, None


def build_service_reminder(car, today=None):
    """Reminder payload for the car's next service, from its latest service record."""
    today = today or timezone.localdate()
    record = car.service_records.order_by("-service_date", "-created_at").first()

    if record is None:
        return {
            "kind": "service",
            "status": Constants.REMINDER_STATUS_DUE_SOON,
            "message": "No service has been logged for this car yet — log your last service to start tracking intervals.",
            "next_due_odometer_km": None,
            "next_due_date": None,
        }

    if record.next_due_odometer_km is None and record.next_due_date is None:
        return {
            "kind": "service",
            "status": Constants.REMINDER_STATUS_OK,
            "message": "No interval set on the last service.",
            "next_due_odometer_km": None,
            "next_due_date": None,
        }

    status, reason = _service_status(car, record, today)

    if status == Constants.REMINDER_STATUS_OK:
        message = "Next service not due yet."
    else:
        message = f"{car.make} {car.model}: {reason}."

    return {
        "kind": "service",
        "status": status,
        "message": message,
        "next_due_odometer_km": record.next_due_odometer_km,
        "next_due_date": record.next_due_date.isoformat() if record.next_due_date else None,
    }


def build_inspection_reminder(car, today=None):
    """
    Reminder payload for a general inspection, so the owner knows the overall
    state of the vehicle. Defaults to every INSPECTION_DEFAULT_INTERVAL_MONTHS
    months after the last inspection (or immediately if none was ever logged).
    """
    today = today or timezone.localdate()
    inspection = car.inspections.order_by("-inspection_date", "-created_at").first()

    if inspection is None:
        return {
            "kind": "inspection",
            "status": Constants.REMINDER_STATUS_DUE_SOON,
            "message": "No general inspection on record — book one to know the state of your vehicle.",
            "next_due_date": None,
        }

    next_due = inspection.next_inspection_date or (
        inspection.inspection_date + relativedelta(months=Constants.INSPECTION_DEFAULT_INTERVAL_MONTHS)
    )

    days_remaining = (next_due - today).days
    if days_remaining <= 0:
        status = Constants.REMINDER_STATUS_OVERDUE
        message = f"General inspection was due on {next_due.isoformat()} — book one to know the state of your vehicle."
    elif days_remaining <= Constants.REMINDER_DUE_SOON_DAYS:
        status = Constants.REMINDER_STATUS_DUE_SOON
        message = f"General inspection due on {next_due.isoformat()}."
    else:
        status = Constants.REMINDER_STATUS_OK
        message = "Next general inspection not due yet."

    return {
        "kind": "inspection",
        "status": status,
        "message": message,
        "next_due_date": next_due.isoformat(),
    }


def build_car_reminders(car, today=None):
    """All reminders for a car — service interval and general inspection."""
    today = today or timezone.localdate()
    return [
        build_service_reminder(car, today),
        build_inspection_reminder(car, today),
    ]
