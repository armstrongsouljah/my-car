from django.urls import path

from expenses.views import ExpenseListCreateView, ExpenseDetailView, ExpenseAnalyticsView

urlpatterns = [
    path("", ExpenseListCreateView.as_view(), name="expense-list-create"),
    path("analytics/", ExpenseAnalyticsView.as_view(), name="expense-analytics"),
    path("<uuid:pk>/", ExpenseDetailView.as_view(), name="expense-detail"),
]
