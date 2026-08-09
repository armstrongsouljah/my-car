import os
import subprocess
import sys

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
        # settings.APP_VERSION is resolved once at import time from the
        # process environment, so override_settings can't exercise the real
        # default — and this process's own env may already have APP_VERSION
        # set. Check the actual default in a clean subprocess instead.
        env = {k: v for k, v in os.environ.items() if k != "APP_VERSION"}
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import django; django.setup(); "
                "from django.conf import settings; "
                "print(settings.APP_VERSION)",
            ],
            env={**env, "DJANGO_SETTINGS_MODULE": "config.test_settings"},
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.stdout.strip() == "dev"
