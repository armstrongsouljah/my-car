from django.urls import path

from expenses.views import (
    ExpenseAnalyticsView,
    ExpenseDetailView,
    ExpenseListCreateView,
    ExpenseMonthlyReportPDFView,
    ExpenseMonthlyReportView,
)

urlpatterns = [
    path("", ExpenseListCreateView.as_view(), name="expense-list-create"),
    path("analytics/", ExpenseAnalyticsView.as_view(), name="expense-analytics"),
    path("reports/<int:year>-<int:month>/", ExpenseMonthlyReportView.as_view(), name="expense-monthly-report"),
    path(
        "reports/<int:year>-<int:month>/pdf/",
        ExpenseMonthlyReportPDFView.as_view(),
        name="expense-monthly-report-pdf",
    ),
    path("<uuid:pk>/", ExpenseDetailView.as_view(), name="expense-detail"),
]
