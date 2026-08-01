from datetime import MAXYEAR, MINYEAR, date

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cars.models import Car
from expenses.models import Expense
from expenses.reports import build_monthly_report
from expenses.serializers import (
    ExpenseCreateSerializer,
    ExpenseDetailSerializer,
    ExpenseEditSerializer,
    ExpenseListSerializer,
)
from utils import QueryParams
from utils.Currency import convert_amount, load_latest_rates
from utils.Exception import CustomValidation
from utils.Views import SmartAPIView, SmartDetailView, SmartPaginationAPIView


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

    def get_serializer_context(self):
        # Loaded once per request rather than per-row inside the
        # serializer's display_amount field — see #40's DisplayAmountMixin.
        context = super().get_serializer_context()
        context["rates"] = load_latest_rates()
        return context

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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["rates"] = load_latest_rates()
        return context

    def queryset(self, **kwargs):
        return Expense.objects.filter(pk=kwargs.get("pk"), car__owner=self.request.user)


class ExpenseAnalyticsView(SmartAPIView):
    """
    Month-on-month expense analytics.

    GET params:
    - ?car=<uuid>     scope to one car (defaults to all the owner's cars)
    - ?year=<int>     a specific calendar year, Jan through Dec — or through
                       the current month if it's the current year, since a
                       future month has nothing to show yet.
    - ?months=<int>   trailing N months ending at the current one, instead
                       of a calendar year — used by the reports page's
                       month picker (?months=24), which wants a rolling
                       window rather than a Jan-anchored one.

    Defaults (no params) to the current calendar year (see #58) rather than
    a trailing-12-months window, which could span two different years and
    read oddly next to a "this year" framing.

    Returns one row per month with the total, per-category breakdown, and the
    change (absolute and percentage) versus the previous calendar month —
    computed by month key, not by list position, so a gap month with no data
    can't make two non-adjacent months look adjacent. Months before the
    account's date_joined are omitted unless they have real logged data (see
    #60) — a month the user was never signed up for isn't "$0 spent."
    """
    permission_classes = [IsAuthenticated]

    # QueryParams.get_int only validates that ?months= parses as an int, not
    # that it's a sane window size — clamp it here so an out-of-range value
    # (0, negative, or huge) can't feed a malformed range()/list slice below.
    MAX_MONTHS = 60

    def _window_keys(self, current_month, year_param, months_param):
        if year_param is not None:
            year = max(MINYEAR, min(year_param, MAXYEAR))
            if year > current_month.year:
                return []
            last_month_num = current_month.month if year == current_month.year else 12
            return [date(year, m, 1).isoformat() for m in range(1, last_month_num + 1)]

        if months_param is not None:
            months = max(1, min(months_param, self.MAX_MONTHS))
            return [(current_month - relativedelta(months=offset)).isoformat() for offset in range(months - 1, -1, -1)]

        return [date(current_month.year, m, 1).isoformat() for m in range(1, current_month.month + 1)]

    def get(self, request, **kwargs):
        year_param = QueryParams.get_int(request, "year")
        months_param = QueryParams.get_int(request, "months")
        target_currency = request.user.currency
        rates = load_latest_rates()

        queryset = Expense.objects.filter(car__owner=request.user)

        car_id = QueryParams.get_str(request, "car")
        if car_id:
            queryset = queryset.filter(car_id=car_id)

        def month_key(value):
            return value.date().isoformat() if hasattr(value, "date") else value.isoformat()

        # Grouped by currency too, not just month/category: an owner may
        # have changed currency over time (see #40), so a month or category
        # can span expenses recorded in more than one — SQL Sum() can't mix
        # those, so each currency's own subtotal is converted and combined
        # here in Python instead of at the DB level.
        monthly_currency_rows = (
            queryset
            .annotate(month=TruncMonth("expense_date"))
            .values("month", "currency")
            .annotate(total=Sum("amount"), count=Count("id"))
        )

        monthly_totals = {}
        monthly_counts = {}
        for row in monthly_currency_rows:
            key = month_key(row["month"])
            converted = float(convert_amount(row["total"], row["currency"], target_currency, rates))
            monthly_totals[key] = monthly_totals.get(key, 0.0) + converted
            monthly_counts[key] = monthly_counts.get(key, 0) + row["count"]

        # Anchor the window to the real current month/year rather than to
        # "the last month with data" — otherwise once a new month starts
        # before any expense is logged in it, the previous month's total
        # silently stands in as "this month" on the frontend (see #56).
        current_month = timezone.localdate().replace(day=1)
        window_keys = self._window_keys(current_month, year_param, months_param)

        # Don't zero-fill a month from before the account existed — that's
        # not "nothing spent that month", it's a month the user was never on
        # the app for (see #60). A month that already has real logged data
        # (e.g. a backdated historical service entered after signup) still
        # shows regardless of when it falls; only the *manufactured* zero
        # entries are excluded. Checked before the zero-fill loop below, so
        # `key in monthly_totals` here only ever reflects real DB rows.
        join_month = timezone.localtime(request.user.date_joined).date().replace(day=1)
        window_keys = [key for key in window_keys if key in monthly_totals or date.fromisoformat(key) >= join_month]

        # Zero-fill every remaining month in the window that has no rows.
        for key in window_keys:
            monthly_totals.setdefault(key, 0.0)
            monthly_counts.setdefault(key, 0)

        by_category_currency_rows = (
            queryset
            .annotate(month=TruncMonth("expense_date"))
            .values("month", "category", "currency")
            .annotate(total=Sum("amount"))
        )

        categories_by_month = {}
        for row in by_category_currency_rows:
            key = month_key(row["month"])
            converted = float(convert_amount(row["total"], row["currency"], target_currency, rates))
            month_categories = categories_by_month.setdefault(key, {})
            month_categories[row["category"]] = month_categories.get(row["category"], 0.0) + converted

        results = []
        for key in window_keys:
            total = round(monthly_totals[key], 2)

            prev_key = (date.fromisoformat(key) - relativedelta(months=1)).isoformat()
            previous_total = monthly_totals.get(prev_key)

            change = None
            change_percent = None
            if previous_total is not None:
                previous_total = round(previous_total, 2)
                change = round(total - previous_total, 2)
                if previous_total > 0:
                    change_percent = round((total - previous_total) / previous_total * 100, 1)

            results.append({
                "month": key,
                "total": total,
                "count": monthly_counts[key],
                "by_category": categories_by_month.get(key, {}),
                "change_vs_previous_month": change,
                "change_percent_vs_previous_month": change_percent,
            })

        grand_total = sum(row["total"] for row in results)
        return Response({
            "months": results,
            "grand_total": round(grand_total, 2),
            "currency": target_currency,
        }, status=status.HTTP_200_OK)


def _validate_period(year, month):
    """
    The <int:year>-<int:month> URL converters only guarantee digits, not a
    real calendar period — month=13 or a year outside datetime's supported
    range would otherwise reach date(year, month, 1) inside
    build_monthly_report and raise an unhandled ValueError (500). January of
    MINYEAR is excluded too: build_monthly_report computes the previous
    month as (year - 1, 12) when month == 1, and MINYEAR - 1 underflows
    datetime's supported range the same way.
    """
    valid_year = MINYEAR <= year <= MAXYEAR and not (year == MINYEAR and month == 1)
    if not valid_year or not (1 <= month <= 12):
        raise CustomValidation("Not a valid year/month.", field="detail", status_code=status.HTTP_400_BAD_REQUEST)


class ExpenseMonthlyReportView(SmartAPIView):
    """
    GET /expenses/reports/<year>-<month>/ — the owner's category/car
    breakdown for one calendar month, for the in-app reports view (see #21).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, year, month, **kwargs):
        year, month = int(year), int(month)
        _validate_period(year, month)
        report = build_monthly_report(request.user, year, month)
        return Response(report, status=status.HTTP_200_OK)


class ExpenseMonthlyReportPDFView(SmartAPIView):
    """
    GET /expenses/reports/<year>-<month>/pdf/ — the same report, rendered to
    PDF via WeasyPrint from the reports/monthly_expense_report.html template.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, year, month, **kwargs):
        year, month = int(year), int(month)
        _validate_period(year, month)

        # Imported lazily, same convention as utils.Email's senders: keeps
        # this module import-safe (no WeasyPrint/Pango load) for every
        # request that isn't downloading a PDF — and only after validation,
        # so a malformed period 400s without paying for that import at all.
        from weasyprint import HTML

        report = build_monthly_report(request.user, year, month)
        html = render_to_string("reports/monthly_expense_report.html", {
            "report": report,
            "user": request.user,
        })
        pdf_bytes = HTML(string=html).write_pdf()

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="glavbox-expenses-{year}-{month:02d}.pdf"'
        )
        return response
