from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

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
    path(f"{API_PREFIX}history-import/", include("history_import.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
