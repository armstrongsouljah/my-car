"""
Redis-backed caching for car information.

Car payloads change rarely relative to how often they are read (dashboard,
detail screens, reminder sweeps), so detail and list responses are cached in
Redis and invalidated whenever the car — or anything that feeds its computed
state (service records, inspections) — changes.
"""
from django.conf import settings
from django.core.cache import cache

CAR_DETAIL_KEY = "car:detail:{car_id}"
CAR_LIST_KEY = "car:list:{owner_id}"


def _ttl():
    return getattr(settings, "CAR_CACHE_TTL_SECONDS", 900)


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
