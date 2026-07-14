from django.urls import path

from inspections.views import InspectionListCreateView, InspectionDetailView

urlpatterns = [
    path("", InspectionListCreateView.as_view(), name="inspection-list-create"),
    path("<uuid:pk>/", InspectionDetailView.as_view(), name="inspection-detail"),
]
