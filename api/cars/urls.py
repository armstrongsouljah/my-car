from django.urls import path

from cars.views import CarListCreateView, CarBulkCreateView, CarCatalogView, CarDetailView

urlpatterns = [
    path("", CarListCreateView.as_view(), name="car-list-create"),
    path("bulk/", CarBulkCreateView.as_view(), name="car-bulk-create"),
    path("catalog/", CarCatalogView.as_view(), name="car-catalog"),
    path("<uuid:pk>/", CarDetailView.as_view(), name="car-detail"),
]
