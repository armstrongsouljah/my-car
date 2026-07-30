"""
Redis-backed caching for data that's read far more often than it changes.

Two policies live here:

- Car detail/list: a flat TTL (`CAR_CACHE_TTL_SECONDS`, default 900s) plus
  write-triggered invalidation. Good enough because staleness self-heals
  within minutes even if an invalidation hook is ever missed.
- Everything else added since: cached until the next local midnight, plus
  write-triggered invalidation. These endpoints' "freshness" is often driven
  by the calendar, not just writes — reminder/service status is computed
  against `timezone.localdate()` (see reminders/engine.py and
  services/reminders.py), so a status can flip from a day passing alone.
  Midnight is the precise boundary for that; a short TTL would just be
  papering over it by recomputing often.
"""
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

CAR_DETAIL_KEY = "car:detail:{car_id}"
CAR_LIST_KEY = "car:list:{owner_id}"

EXCHANGE_RATES_KEY = "expenses:exchange_rates"

REMINDER_CATALOG_KEY = "reminders:catalog"
REMINDER_LIST_KEY = "reminders:list:{owner_id}"
SERVICE_DIGEST_KEY = "services:digest:{owner_id}"
SERVICE_LIST_KEY = "services:list:{car_id}"
INSPECTION_LIST_KEY = "inspections:list:{car_id}"


def _ttl():
    return getattr(settings, "CAR_CACHE_TTL_SECONDS", 900)


def _seconds_until_midnight():
    now = timezone.localtime()
    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((next_midnight - now).total_seconds()))


def _set_until_midnight(key, data):
    cache.set(key, data, _seconds_until_midnight())


def get_car_detail(car_id):
    return cache.get(CAR_DETAIL_KEY.format(car_id=car_id))


def set_car_detail(car_id, data):
    cache.set(CAR_DETAIL_KEY.format(car_id=car_id), data, _ttl())


def get_car_list(owner_id):
    return cache.get(CAR_LIST_KEY.format(owner_id=owner_id))


def set_car_list(owner_id, data):
    cache.set(CAR_LIST_KEY.format(owner_id=owner_id), data, _ttl())


def invalidate_car(car_id, owner_id=None):
    """Drop the cached detail for a car and, when known, its owner's list."""
    cache.delete(CAR_DETAIL_KEY.format(car_id=car_id))
    if owner_id is not None:
        cache.delete(CAR_LIST_KEY.format(owner_id=owner_id))


def invalidate_owner(owner_id):
    cache.delete(CAR_LIST_KEY.format(owner_id=owner_id))


# ── Exchange rates: global, changes at most once a day (refresh_exchange_rates_task) ──

def get_exchange_rates():
    return cache.get(EXCHANGE_RATES_KEY)


def set_exchange_rates(data):
    _set_until_midnight(EXCHANGE_RATES_KEY, data)


def invalidate_exchange_rates():
    cache.delete(EXCHANGE_RATES_KEY)


# ── Reminder catalog: static, global, essentially never changes ───────────────

def get_reminder_catalog():
    return cache.get(REMINDER_CATALOG_KEY)


def set_reminder_catalog(data):
    _set_until_midnight(REMINDER_CATALOG_KEY, data)


# ── Reminders list: per owner, the unfiltered `GET /reminders/` response ──────

def get_reminders(owner_id):
    return cache.get(REMINDER_LIST_KEY.format(owner_id=owner_id))


def set_reminders(owner_id, data):
    _set_until_midnight(REMINDER_LIST_KEY.format(owner_id=owner_id), data)


def invalidate_reminders(owner_id):
    cache.delete(REMINDER_LIST_KEY.format(owner_id=owner_id))


# ── Service/inspection digest (`GET /services/reminders/`): per owner ─────────

def get_service_digest(owner_id):
    return cache.get(SERVICE_DIGEST_KEY.format(owner_id=owner_id))


def set_service_digest(owner_id, data):
    _set_until_midnight(SERVICE_DIGEST_KEY.format(owner_id=owner_id), data)


def invalidate_service_digest(owner_id):
    cache.delete(SERVICE_DIGEST_KEY.format(owner_id=owner_id))


# ── Service record / inspection lists: per car (`?car=` is the common case) ───

def get_service_list(car_id):
    return cache.get(SERVICE_LIST_KEY.format(car_id=car_id))


def set_service_list(car_id, data):
    _set_until_midnight(SERVICE_LIST_KEY.format(car_id=car_id), data)


def invalidate_service_list(car_id):
    cache.delete(SERVICE_LIST_KEY.format(car_id=car_id))


def get_inspection_list(car_id):
    return cache.get(INSPECTION_LIST_KEY.format(car_id=car_id))


def set_inspection_list(car_id, data):
    _set_until_midnight(INSPECTION_LIST_KEY.format(car_id=car_id), data)


def invalidate_inspection_list(car_id):
    cache.delete(INSPECTION_LIST_KEY.format(car_id=car_id))
