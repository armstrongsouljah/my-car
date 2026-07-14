from django.urls import path

from cars.views import CarListCreateView, CarDetailView

urlpatterns = [
    path("", CarListCreateView.as_view(), name="car-list-create"),
    path("<uuid:pk>/", CarDetailView.as_view(), name="car-detail"),
]
