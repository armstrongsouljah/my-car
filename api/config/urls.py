from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include, re_path
from django.views.static import serve as serve_static

API_PREFIX = "api/v1/"


def health(_request):
    return JsonResponse({"status": "ok", "version": settings.APP_VERSION})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path(f"{API_PREFIX}auth/", include("accounts.urls")),
    path(f"{API_PREFIX}cars/", include("cars.urls")),
    path(f"{API_PREFIX}services/", include("services.urls")),
    path(f"{API_PREFIX}inspections/", include("inspections.urls")),
    path(f"{API_PREFIX}reminders/", include("reminders.urls")),
    path(f"{API_PREFIX}expenses/", include("expenses.urls")),
    path(f"{API_PREFIX}assistant/", include("assistant.urls")),
    path(f"{API_PREFIX}support/", include("support.urls")),
]

# Django's own `django.conf.urls.static.static()` helper silently no-ops
# unless DEBUG=True -- fine for most apps (a real deployment normally has a
# CDN/reverse proxy serve media directly), but this one doesn't: Caddy just
# reverse-proxies every request on api(-dev).glavbox.com straight through to
# this container (see repo-root Caddyfile) with no separate static-file
# layer for MEDIA_ROOT. Without Django serving /media/ itself, an uploaded
# Inspection.report (the only local-disk upload in this app -- see #33/#145)
# was completely unreachable in every deployed environment, 404 regardless
# of host. Wired directly via django.views.static.serve instead of the
# DEBUG-gated helper, so it works the same in dev/prod as it already does
# locally.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve_static, {"document_root": settings.MEDIA_ROOT}),
]
