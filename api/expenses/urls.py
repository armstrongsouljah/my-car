from django.urls import path

from expenses.views import (
    ExpenseAllTimeReportPDFView,
    ExpenseAllTimeReportView,
    ExpenseAnalyticsView,
    ExpenseDetailView,
    ExpenseListCreateView,
    ExpenseMonthlyReportPDFView,
    ExpenseMonthlyReportView,
)

urlpatterns = [
    path("", ExpenseListCreateView.as_view(), name="expense-list-create"),
    path("analytics/", ExpenseAnalyticsView.as_view(), name="expense-analytics"),
    # Listed before <int:year>-<int:month>/ for clarity, though there's no
    # actual ambiguity — that converter only matches digits, so "all-time"
    # can never match it.
    path("reports/all-time/", ExpenseAllTimeReportView.as_view(), name="expense-all-time-report"),
    path("reports/all-time/pdf/", ExpenseAllTimeReportPDFView.as_view(), name="expense-all-time-report-pdf"),
    path("reports/<int:year>-<int:month>/", ExpenseMonthlyReportView.as_view(), name="expense-monthly-report"),
    path(
        "reports/<int:year>-<int:month>/pdf/",
        ExpenseMonthlyReportPDFView.as_view(),
        name="expense-monthly-report-pdf",
    ),
    path("<uuid:pk>/", ExpenseDetailView.as_view(), name="expense-detail"),
]
