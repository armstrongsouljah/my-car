import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestHealth:
    """See #74 — the version comes from settings.APP_VERSION, itself set by
    the deploy workflow (the release tag for prod, "dev-<sha>" for dev)."""

    def test_reports_ok_and_the_configured_version(self):
        with override_settings(APP_VERSION="v1.2.3"):
            response = APIClient().get("/health/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "v1.2.3"}

    def test_defaults_to_dev_when_unset(self):
        response = APIClient().get("/health/")

        assert response.json()["version"] == "dev"
