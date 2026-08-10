from django.urls import path

from cars.views import (
    CarBulkCreateView,
    CarCatalogView,
    CarDetailView,
    CarListCreateView,
    CarServiceHistoryReportPDFView,
)

urlpatterns = [
    path("", CarListCreateView.as_view(), name="car-list-create"),
    path("bulk/", CarBulkCreateView.as_view(), name="car-bulk-create"),
    path("catalog/", CarCatalogView.as_view(), name="car-catalog"),
    path("<uuid:pk>/", CarDetailView.as_view(), name="car-detail"),
    path(
        "<uuid:pk>/service-history/pdf/",
        CarServiceHistoryReportPDFView.as_view(),
        name="car-service-history-report-pdf",
    ),
]
