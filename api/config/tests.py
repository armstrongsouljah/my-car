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


@pytest.mark.django_db
class TestMediaServing:
    """See #33/#145 -- Django's own static.static() helper (what urls.py
    used before) silently no-ops unless DEBUG=True, which every deployed
    environment correctly sets False. Caddy has no separate static-file
    layer for MEDIA_ROOT (see repo-root Caddyfile) -- it just reverse-
    proxies straight through to this container -- so without Django
    serving /media/ itself, every uploaded Inspection.report was a 404
    in every deployed environment, regardless of host.

    Writes into the *real* settings.MEDIA_ROOT rather than
    override_settings(MEDIA_ROOT=...) -- urls.py's document_root kwarg is
    bound to settings.MEDIA_ROOT once at urlconf import time, not
    re-read per request, so overriding the setting in a test wouldn't
    actually retarget the already-registered view (a test-only quirk;
    MEDIA_ROOT never changes at runtime in a real deployment)."""

    def test_serves_an_existing_file_even_with_debug_false(self, settings):
        media_dir = settings.MEDIA_ROOT / "inspection_reports"
        media_dir.mkdir(parents=True, exist_ok=True)
        report_path = media_dir / "test_report.txt"
        report_path.write_text("hello")
        settings.DEBUG = False

        try:
            response = APIClient().get("/media/inspection_reports/test_report.txt")
        finally:
            report_path.unlink()

        assert response.status_code == 200
        assert b"".join(response.streaming_content) == b"hello"

    def test_404s_for_a_path_that_does_not_exist(self, settings):
        settings.DEBUG = False

        response = APIClient().get("/media/inspection_reports/does-not-exist.txt")

        assert response.status_code == 404
