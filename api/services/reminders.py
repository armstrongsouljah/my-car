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


def _within_new_car_grace_period(car, today):
    if car.created_at is None:
        return False
    return (today - car.created_at.date()).days < Constants.REMINDER_NEW_CAR_GRACE_DAYS


def _progress_percent(baseline_km, next_km, current_km, baseline_date, next_date, today):
    """% of the way from baseline to next-due — mirrors reminders/engine.py's
    version (each app keeps its own copy rather than sharing one, matching
    this module's existing self-contained-per-model convention)."""
    percentages = []

    if baseline_km is not None and next_km is not None:
        span = next_km - baseline_km
        if span > 0:
            percentages.append((current_km - baseline_km) / span * 100)

    if baseline_date is not None and next_date is not None:
        span = (next_date - baseline_date).days
        if span > 0:
            percentages.append((today - baseline_date).days / span * 100)

    if not percentages:
        return 0

    return max(0, min(100, round(max(percentages))))


def build_service_reminder(car, today=None):
    """Reminder payload for the car's next service, from its latest service record."""
    today = today or timezone.localdate()
    # By odometer, not service_date -- a car's mileage only ever goes up, so
    # the highest-odometer record is unambiguously the most recent one in
    # the car's actual life, whereas service_date is user-entered and can
    # be backdated/out of order (e.g. a minor service logged with a later
    # calendar date than an earlier, higher-mileage full service). Using
    # service_date let an older, lower-mileage record's own stale next-due
    # threshold outrank a newer one that already covers the same interval.
    record = car.service_records.order_by("-odometer_km", "-service_date").first()

    if record is None:
        if _within_new_car_grace_period(car, today):
            return {
                "kind": "service",
                "status": Constants.REMINDER_STATUS_OK,
                "message": "No service logged yet — log your last service to start tracking intervals.",
                "progress_percent": 0,
            }
        return {
            "kind": "service",
            "status": Constants.REMINDER_STATUS_DUE_SOON,
            "message": "No service has been logged for this car yet — log your last service to start tracking intervals.",
            "progress_percent": 0,
        }

    if record.next_due_odometer_km is None and record.next_due_date is None:
        return {
            "kind": "service",
            "status": Constants.REMINDER_STATUS_OK,
            "message": "No interval set on the last service.",
            "progress_percent": 0,
        }

    status, reason = _service_status(car, record, today)

    if status == Constants.REMINDER_STATUS_OK:
        message = "Next service not due yet."
    else:
        message = f"{car.make} {car.model}: {reason}."

    progress_percent = _progress_percent(
        record.odometer_km, record.next_due_odometer_km, car.current_odometer_km,
        record.service_date, record.next_due_date, today,
    )

    return {
        "kind": "service",
        "status": status,
        "message": message,
        "progress_percent": progress_percent,
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
        if _within_new_car_grace_period(car, today):
            return {
                "kind": "inspection",
                "status": Constants.REMINDER_STATUS_OK,
                "message": "No general inspection on record yet — book one to know the state of your vehicle.",
                "progress_percent": 0,
            }
        return {
            "kind": "inspection",
            "status": Constants.REMINDER_STATUS_DUE_SOON,
            "message": "No general inspection on record — book one to know the state of your vehicle.",
            "progress_percent": 0,
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

    progress_percent = _progress_percent(
        None, None, None, inspection.inspection_date, next_due, today,
    )

    return {
        "kind": "inspection",
        "status": status,
        "message": message,
        "progress_percent": progress_percent,
    }


def build_car_reminders(car, today=None):
    """All reminders for a car — service interval and general inspection."""
    today = today or timezone.localdate()
    return [
        build_service_reminder(car, today),
        build_inspection_reminder(car, today),
    ]
