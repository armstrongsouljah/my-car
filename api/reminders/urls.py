from django.urls import path

from reminders.views import (
    ReminderCatalogView,
    ReminderCompleteView,
    ReminderDetailView,
    ReminderListCreateView,
)

urlpatterns = [
    path("", ReminderListCreateView.as_view(), name="reminder-list-create"),
    path("catalog/", ReminderCatalogView.as_view(), name="reminder-catalog"),
    path("<uuid:pk>/", ReminderDetailView.as_view(), name="reminder-detail"),
    path("<uuid:pk>/complete/", ReminderCompleteView.as_view(), name="reminder-complete"),
]
