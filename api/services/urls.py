from django.urls import path

from services.views import ServiceRecordListCreateView, ServiceRecordDetailView, RemindersView

urlpatterns = [
    path("", ServiceRecordListCreateView.as_view(), name="service-list-create"),
    path("reminders/", RemindersView.as_view(), name="service-reminders"),
    path("<uuid:pk>/", ServiceRecordDetailView.as_view(), name="service-detail"),
]
