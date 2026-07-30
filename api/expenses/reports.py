from datetime import date

from django.db.models import Count, Sum

from expenses.models import Expense
from utils import Constants


def build_monthly_report(user, year: int, month: int) -> dict:
    """
    Aggregates one user's expenses, across all their cars, for a single
    calendar month. This is the one source of truth behind the in-app
    report, the downloadable PDF, and the monthly email digest — see #21 —
    so the numbers on all three surfaces can't drift apart.
    """
    queryset = Expense.objects.filter(car__owner=user, expense_date__year=year, expense_date__month=month)

    total = queryset.aggregate(total=Sum("amount"))["total"] or 0
    count = queryset.count()

    category_labels = dict(Constants.EXPENSE_CATEGORIES)
    by_category = [
        {
            "category": row["category"],
            "category_label": category_labels.get(row["category"], row["category"]),
            "total": float(row["total"]),
            "count": row["count"],
        }
        for row in queryset.values("category").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
    ]

    by_car = [
        {
            "car_id": str(row["car_id"]),
            "label": f"{row['car__make']} {row['car__model']}"
            + (f" — {row['car__registration_number']}" if row["car__registration_number"] else ""),
            "total": float(row["total"]),
            "count": row["count"],
        }
        for row in queryset.values("car_id", "car__make", "car__model", "car__registration_number")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    ]

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    previous_total = float(
        Expense.objects.filter(
            car__owner=user, expense_date__year=prev_year, expense_date__month=prev_month
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    change = round(float(total) - previous_total, 2)
    change_percent = round(change / previous_total * 100, 1) if previous_total else None

    return {
        "year": year,
        "month": month,
        "month_label": date(year, month, 1).strftime("%B %Y"),
        "total": float(total),
        "count": count,
        "by_category": by_category,
        "by_car": by_car,
        "previous_month_total": previous_total,
        "change_vs_previous_month": change,
        "change_percent_vs_previous_month": change_percent,
    }
