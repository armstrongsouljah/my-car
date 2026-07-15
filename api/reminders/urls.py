from django.urls import path

from reminders.views import ReminderListCreateView, ReminderDetailView, ReminderCatalogView

urlpatterns = [
    path("", ReminderListCreateView.as_view(), name="reminder-list-create"),
    path("catalog/", ReminderCatalogView.as_view(), name="reminder-catalog"),
    path("<uuid:pk>/", ReminderDetailView.as_view(), name="reminder-detail"),
]
