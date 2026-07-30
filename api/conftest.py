import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """
    Django's cache backend (including locmem in tests) lives outside the DB
    transaction pytest-django wraps each test in, so anything cached under a
    global (non-owner/car-scoped) key — e.g. utils.Cache's exchange-rates or
    reminder-catalog cache — would otherwise leak between tests instead of
    resetting along with the DB.
    """
    cache.clear()
    yield
    cache.clear()
