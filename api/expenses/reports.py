from datetime import date

from django.db.models import Count, Sum

from expenses.models import Expense
from utils import Constants
from utils.Currency import convert_amount, load_latest_rates


def _converted_total(rows, target_currency, rates):
    """
    Sums each currency's own SQL subtotal after converting it to
    `target_currency` — see #40. An owner may have changed currency over
    time, so `rows` (each a {"currency": ..., "total": ...} dict from a
    values().annotate(total=Sum("amount")) query) can span more than one
    currency; SQL Sum() can't mix those, so the conversion and combining
    happens here in Python instead.
    """
    return sum((float(convert_amount(row["total"], row["currency"], target_currency, rates)) for row in rows), 0.0)


def build_monthly_report(user, year: int, month: int) -> dict:
    """
    Aggregates one user's expenses, across all their cars, for a single
    calendar month. This is the one source of truth behind the in-app
    report, the downloadable PDF, and the monthly email digest — see #21 —
    so the numbers on all three surfaces can't drift apart.
    """
    queryset = Expense.objects.filter(car__owner=user, expense_date__year=year, expense_date__month=month)
    target_currency = user.currency
    rates = load_latest_rates()

    totals_by_currency = queryset.values("currency").annotate(total=Sum("amount"))
    total = round(_converted_total(totals_by_currency, target_currency, rates), 2)
    count = queryset.count()

    category_labels = dict(Constants.EXPENSE_CATEGORIES)
    category_totals = {}
    for row in queryset.values("category", "currency").annotate(total=Sum("amount"), count=Count("id")):
        entry = category_totals.setdefault(row["category"], {"total": 0.0, "count": 0})
        entry["total"] += float(convert_amount(row["total"], row["currency"], target_currency, rates))
        entry["count"] += row["count"]
    by_category = sorted(
        (
            {
                "category": category,
                "category_label": category_labels.get(category, category),
                "total": round(data["total"], 2),
                "count": data["count"],
            }
            for category, data in category_totals.items()
        ),
        key=lambda row: -row["total"],
    )

    car_totals = {}
    car_rows = queryset.values(
        "car_id", "car__make", "car__model", "car__registration_number", "currency"
    ).annotate(total=Sum("amount"), count=Count("id"))
    for row in car_rows:
        entry = car_totals.setdefault(
            row["car_id"],
            {
                "label": f"{row['car__make']} {row['car__model']}"
                + (f" — {row['car__registration_number']}" if row["car__registration_number"] else ""),
                "total": 0.0,
                "count": 0,
            },
        )
        entry["total"] += float(convert_amount(row["total"], row["currency"], target_currency, rates))
        entry["count"] += row["count"]
    by_car = sorted(
        (
            {"car_id": str(car_id), "label": data["label"], "total": round(data["total"], 2), "count": data["count"]}
            for car_id, data in car_totals.items()
        ),
        key=lambda row: -row["total"],
    )

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    previous_totals_by_currency = Expense.objects.filter(
        car__owner=user, expense_date__year=prev_year, expense_date__month=prev_month
    ).values("currency").annotate(total=Sum("amount"))
    previous_total = round(_converted_total(previous_totals_by_currency, target_currency, rates), 2)

    change = round(total - previous_total, 2)
    change_percent = round(change / previous_total * 100, 1) if previous_total else None

    return {
        "year": year,
        "month": month,
        "month_label": date(year, month, 1).strftime("%B %Y"),
        "total": total,
        "count": count,
        "by_category": list(by_category),
        "by_car": list(by_car),
        "previous_month_total": previous_total,
        "change_vs_previous_month": change,
        "change_percent_vs_previous_month": change_percent,
        # See #40 — the single source of truth for currency on this report,
        # so the in-app view, PDF, and email digest can't drift on it either.
        # Blank means the owner has no currency set; renderers fall back to
        # a bare number.
        "currency": target_currency,
    }
