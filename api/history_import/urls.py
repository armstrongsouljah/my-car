from django.urls import path

from history_import.views import ServiceHistoryExtractView, ServiceHistoryImportView

urlpatterns = [
    path("extract/", ServiceHistoryExtractView.as_view(), name="history-import-extract"),
    path("confirm/", ServiceHistoryImportView.as_view(), name="history-import-confirm"),
]
