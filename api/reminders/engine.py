"""
Status/progress engine for user-configured `Reminder`s — evaluates
"whichever comes first" (by date, by mileage, or both) against the car's
current state. Deliberately self-contained (no import from
`services/reminders.py`): the two modules evaluate different models and
each app owns its own compute logic, same as `ServiceRecord` and
`Inspection` already do.

Status semantics match `services/reminders.py`:
- overdue:  the km threshold has been passed OR the date has passed.
- due_soon: within REMINDER_DUE_SOON_KM km or REMINDER_DUE_SOON_DAYS days.
- ok:       neither threshold is near.
"""
from datetime import timedelta

from django.utils import timezone
from django.utils.timesince import timeuntil

from utils import Constants


def _bucket(remaining, due_soon_threshold):
    if remaining <= 0:
        return Constants.REMINDER_STATUS_OVERDUE
    if remaining <= due_soon_threshold:
        return Constants.REMINDER_STATUS_DUE_SOON
    return Constants.REMINDER_STATUS_OK


def _worst(statuses):
    for status in (Constants.REMINDER_STATUS_OVERDUE, Constants.REMINDER_STATUS_DUE_SOON):
        if status in statuses:
            return status
    return Constants.REMINDER_STATUS_OK


def _progress_percent(reminder, car, today):
    percentages = []

    if reminder.baseline_odometer_km is not None and reminder.next_due_odometer_km:
        span = reminder.next_due_odometer_km - reminder.baseline_odometer_km
        if span > 0:
            percentages.append((car.current_odometer_km - reminder.baseline_odometer_km) / span * 100)

    if reminder.baseline_date is not None and reminder.next_due_date:
        span = (reminder.next_due_date - reminder.baseline_date).days
        if span > 0:
            percentages.append((today - reminder.baseline_date).days / span * 100)

    if not percentages:
        return 0

    return max(0, min(100, round(max(percentages))))


def _build_message(status, remaining_km, remaining_days):
    parts = []

    if remaining_km is not None:
        if remaining_km <= 0:
            parts.append(f"{abs(remaining_km):,} km overdue")
        else:
            parts.append(f"{remaining_km:,} km remaining")

    if remaining_days is not None:
        if remaining_days <= 0:
            parts.append("date passed")
        else:
            due = timezone.localdate() + timedelta(days=remaining_days)
            parts.append(f"in {timeuntil(due)}")

    if not parts:
        return "All good."

    prefix = "All good" if status == Constants.REMINDER_STATUS_OK else "Attention needed"
    return f"{prefix} · {' · '.join(parts)}"


def evaluate_reminder(reminder, today=None):
    today = today or timezone.localdate()
    car = reminder.car

    remaining_km = remaining_days = None
    statuses = []

    if reminder.next_due_odometer_km is not None:
        remaining_km = reminder.next_due_odometer_km - car.current_odometer_km
        statuses.append(_bucket(remaining_km, Constants.REMINDER_DUE_SOON_KM))

    if reminder.next_due_date is not None:
        remaining_days = (reminder.next_due_date - today).days
        statuses.append(_bucket(remaining_days, Constants.REMINDER_DUE_SOON_DAYS))

    status = _worst(statuses)
    progress_percent = _progress_percent(reminder, car, today)
    message = _build_message(status, remaining_km, remaining_days)

    return {
        "status": status,
        "message": message,
        "progress_percent": progress_percent,
        "remaining_km": remaining_km,
        "remaining_days": remaining_days,
    }
