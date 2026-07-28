from django.urls import path

from support.views import SupportRequestView

urlpatterns = [
    path("", SupportRequestView.as_view(), name="support-request"),
]
