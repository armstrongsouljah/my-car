from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utils import QueryParams
from utils.Exception import CustomValidation
from utils.Views import SmartDetailView, SmartPaginationAPIView, SmartAPIView

from cars.models import Car
from expenses.models import Expense
from expenses.serializers import (
    ExpenseCreateSerializer,
    ExpenseEditSerializer,
    ExpenseListSerializer,
    ExpenseDetailSerializer,
)


class ExpenseListCreateView(SmartPaginationAPIView):
    """
    GET  — expense log for the owner's cars (?car=<uuid>, ?category=fuel).
    POST — log a garage visit, modification parts, fuel expense, and so on.
    """
    model = Expense
    create_serializer = ExpenseCreateSerializer
    list_serializer = ExpenseListSerializer
    detail_serializer = ExpenseDetailSerializer
    permission_classes = [IsAuthenticated]

    def override_post_data(self, data):
        data = dict(data)
        car_id = data.get("car")
        if not Car.objects.filter(pk=car_id, owner=self.request.user).exists():
            raise CustomValidation(
                "Car not found in your garage.",
                field="car",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return data

    def filter_queryset(self, **kwargs):
        return Expense.objects.filter(car__owner=self.request.user)

    def add_filters(self, queryset):
        car_id = QueryParams.get_str(self.request, "car")
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        category = QueryParams.get_str(self.request, "category")
        if category:
            queryset = queryset.filter(category=category)
        start_date = QueryParams.get_str(self.request, "start_date")
        if start_date:
            queryset = queryset.filter(expense_date__gte=start_date)
        end_date = QueryParams.get_str(self.request, "end_date")
        if end_date:
            queryset = queryset.filter(expense_date__lte=end_date)
        return queryset


class ExpenseDetailView(SmartDetailView):
    model = Expense
    deletable = True
    detail_serializer = ExpenseDetailSerializer
    edit_serializer = ExpenseEditSerializer
    permission_classes = [IsAuthenticated]

    def queryset(self, **kwargs):
        return Expense.objects.filter(pk=kwargs.get("pk"), car__owner=self.request.user)


class ExpenseAnalyticsView(SmartAPIView):
    """
    Month-on-month expense analytics.

    GET params:
    - ?car=<uuid>     scope to one car (defaults to all the owner's cars)
    - ?months=<int>   how many trailing months to include (default 12)

    Returns one row per month with the total, per-category breakdown, and the
    change (absolute and percentage) versus the previous month.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        months = QueryParams.get_int(request, "months", default_value=12)

        queryset = Expense.objects.filter(car__owner=request.user)

        car_id = QueryParams.get_str(request, "car")
        if car_id:
            queryset = queryset.filter(car_id=car_id)

        monthly = (
            queryset
            .annotate(month=TruncMonth("expense_date"))
            .values("month")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("month")
        )

        by_category = (
            queryset
            .annotate(month=TruncMonth("expense_date"))
            .values("month", "category")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )

        categories_by_month = {}
        for row in by_category:
            key = row["month"].date().isoformat() if hasattr(row["month"], "date") else row["month"].isoformat()
            categories_by_month.setdefault(key, {})[row["category"]] = float(row["total"])

        results = []
        previous_total = None
        for row in monthly:
            month_key = row["month"].date().isoformat() if hasattr(row["month"], "date") else row["month"].isoformat()
            total = float(row["total"])

            change = None
            change_percent = None
            if previous_total is not None:
                change = round(total - previous_total, 2)
                if previous_total > 0:
                    change_percent = round((total - previous_total) / previous_total * 100, 1)

            results.append({
                "month": month_key,
                "total": total,
                "count": row["count"],
                "by_category": categories_by_month.get(month_key, {}),
                "change_vs_previous_month": change,
                "change_percent_vs_previous_month": change_percent,
            })
            previous_total = total

        results = results[-months:]

        grand_total = sum(row["total"] for row in results)
        return Response({
            "months": results,
            "grand_total": round(grand_total, 2),
        }, status=status.HTTP_200_OK)
