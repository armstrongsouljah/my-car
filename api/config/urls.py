from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

API_PREFIX = "api/v1/"


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path(f"{API_PREFIX}auth/", include("accounts.urls")),
    path(f"{API_PREFIX}cars/", include("cars.urls")),
    path(f"{API_PREFIX}services/", include("services.urls")),
    path(f"{API_PREFIX}inspections/", include("inspections.urls")),
    path(f"{API_PREFIX}expenses/", include("expenses.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
