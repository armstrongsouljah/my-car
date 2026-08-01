from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import Car
from expenses.models import ExchangeRate, Expense
from expenses.views import ExpenseAnalyticsView


def previous_month():
    """Year/month one calendar month before "today" — mirrors the task's own calculation."""
    today = timezone.localdate()
    return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)


@pytest.fixture
def owner(db):
    # Backdated well past any window these tests exercise (?months= caps at
    # 60) — an analytics test can freely plant expenses years back without
    # them getting clipped by the #60 "no months before signup" guard.
    # Tests for that guard itself override date_joined explicitly.
    user = User.objects.create_user(
        email="owner@example.com", password="str0ng-pass-123",
        date_joined=timezone.now() - relativedelta(years=10),
    )
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    return user


@pytest.fixture
def car(owner):
    return Car.objects.create(owner=owner, make="Toyota", model="Corolla")


@pytest.fixture
def rates(db):
    """
    UGX/KES rates loosely matching real-world magnitude (not the exact
    figures) — enough to make conversion math legible in assertions.
    """
    today = timezone.localdate()
    ExchangeRate.objects.create(date=today, currency="UGX", rate_to_usd=Decimal("1") / Decimal("3700"))
    ExchangeRate.objects.create(date=today, currency="KES", rate_to_usd=Decimal("1") / Decimal("129"))
    ExchangeRate.objects.create(date=today, currency="USD", rate_to_usd=Decimal("1"))


@pytest.mark.django_db
class TestExpenseCurrencyConversion:
    """See #40 — an expense snapshots the owner's currency at creation, and
    conversion to the owner's *current* currency always uses the latest
    fetched rate, not a rate tied to the transaction's own date."""

    def test_currency_is_snapshotted_from_the_owner_at_creation(self, owner, car):
        owner.currency = "UGX"
        owner.save(update_fields=["currency"])

        expense = Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))

        assert expense.currency == "UGX"

    def test_later_owner_currency_changes_do_not_retroactively_change_old_rows(self, owner, car):
        owner.currency = "UGX"
        owner.save(update_fields=["currency"])
        expense = Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))

        owner.currency = "KES"
        owner.save(update_fields=["currency"])
        expense.refresh_from_db()

        assert expense.currency == "UGX"

    def test_list_endpoint_converts_to_the_owners_currency(self, owner, car, rates):
        owner.currency = "KES"
        owner.save(update_fields=["currency"])
        Expense.objects.create(car=car, category="fuel", amount=3700, currency="UGX", expense_date=date(2026, 5, 10))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/")

        row = (response.data["results"] if "results" in response.data else response.data)[0]
        assert row["display_currency"] == "KES"
        assert round(row["display_amount"], 2) == 129.0

    def test_list_endpoint_falls_back_to_raw_amount_without_rates(self, owner, car):
        owner.currency = "KES"
        owner.save(update_fields=["currency"])
        Expense.objects.create(car=car, category="fuel", amount=3700, currency="UGX", expense_date=date(2026, 5, 10))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/")

        row = (response.data["results"] if "results" in response.data else response.data)[0]
        assert row["display_amount"] == 3700.0


@pytest.mark.django_db
class TestExpenseAnalytics:

    def test_month_on_month_totals_and_change(self, owner, car):
        today = timezone.localdate()
        last_month = today - relativedelta(months=1)
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=last_month.replace(day=10))
        Expense.objects.create(car=car, category="garage_visit", amount=50, expense_date=last_month.replace(day=20))
        Expense.objects.create(car=car, category="fuel", amount=200, expense_date=today)

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/")

        assert response.status_code == 200
        months = response.data["months"]
        # The window is anchored to the real current month (see #56), so
        # index from the end rather than assuming these are the only months.
        assert months[-1]["month"] == today.replace(day=1).isoformat()
        assert months[-2]["total"] == 150.0
        assert months[-2]["by_category"] == {"fuel": 100.0, "garage_visit": 50.0}
        assert months[-1]["total"] == 200.0
        assert months[-1]["change_vs_previous_month"] == 50.0
        assert response.data["grand_total"] == 350.0

    def test_current_month_is_always_present_even_with_no_expenses_yet(self, owner, car):
        """See #56 — before this, a month with no expenses logged yet simply
        never appeared, so the frontend's "last entry = this month" lookup
        would silently show a stale earlier month's total instead of zero."""
        last_month = timezone.localdate() - relativedelta(months=1)
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=last_month.replace(day=10))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/")

        months = response.data["months"]
        assert months[-1]["month"] == timezone.localdate().replace(day=1).isoformat()
        assert months[-1]["total"] == 0.0
        assert months[-1]["count"] == 0

    def test_other_owners_expenses_excluded(self, owner, car, db):
        other = User.objects.create_user(email="other@example.com", password="str0ng-pass-123")
        other_car = Car.objects.create(owner=other, make="Honda", model="Civic")
        today = timezone.localdate()
        Expense.objects.create(car=other_car, category="fuel", amount=999, expense_date=today)
        Expense.objects.create(car=car, category="fuel", amount=10, expense_date=today)

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/")

        assert response.data["grand_total"] == 10.0

    def test_converts_a_month_spanning_two_currencies(self, owner, car, rates):
        """See #40 — an owner who changed currency mid-month has expenses in
        both; SQL Sum() can't mix them, so each currency's subtotal is
        converted to the owner's current currency and combined in Python."""
        owner.currency = "USD"
        owner.save(update_fields=["currency"])
        today = timezone.localdate()
        Expense.objects.create(car=car, category="fuel", amount=3700, currency="UGX", expense_date=today)
        Expense.objects.create(car=car, category="fuel", amount=50, currency="USD", expense_date=today)

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/")

        months = response.data["months"]
        assert round(months[-1]["total"], 2) == 51.0  # 3700 UGX (-> $1) + $50
        assert response.data["currency"] == "USD"

    def test_months_param_is_clamped_to_a_sane_range(self, owner, car):
        """An out-of-range ?months= (unchecked past QueryParams.get_int's
        int-syntax check) shouldn't be able to feed a negative/huge window
        into the range()/list-slice building the response."""
        client = APIClient()
        client.force_authenticate(owner)

        response = client.get("/api/v1/expenses/analytics/?months=-5")
        assert response.status_code == 200
        assert len(response.data["months"]) == 1

        response = client.get("/api/v1/expenses/analytics/?months=0")
        assert response.status_code == 200
        assert len(response.data["months"]) == 1

        response = client.get("/api/v1/expenses/analytics/?months=9999")
        assert response.status_code == 200
        assert len(response.data["months"]) == ExpenseAnalyticsView.MAX_MONTHS

    def test_default_window_is_the_current_calendar_year(self, owner, car):
        """See #58 — a rolling trailing-12-months window can span two
        different calendar years; the chart now shows Jan through the
        current month of *this* year instead.

        Pinned to June rather than using the real "today": in January, a
        Jan-15 planted expense and one dated "today" would collide into the
        same month, making months[0] and months[-1] the same row.
        """
        fixed_today = date(timezone.localdate().year, 6, 15)
        with mock.patch("django.utils.timezone.localdate", return_value=fixed_today):
            Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(fixed_today.year, 1, 15))
            Expense.objects.create(car=car, category="fuel", amount=200, expense_date=fixed_today)

            client = APIClient()
            client.force_authenticate(owner)
            response = client.get("/api/v1/expenses/analytics/")

        months = response.data["months"]
        assert len(months) == fixed_today.month
        assert months[0]["month"] == date(fixed_today.year, 1, 1).isoformat()
        assert months[0]["total"] == 100.0
        assert months[-1]["month"] == fixed_today.replace(day=1).isoformat()
        assert months[-1]["total"] == 200.0

    def test_year_param_returns_a_past_years_full_january_to_december(self, owner, car):
        past_year = timezone.localdate().year - 1
        Expense.objects.create(car=car, category="fuel", amount=75, expense_date=date(past_year, 6, 10))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get(f"/api/v1/expenses/analytics/?year={past_year}")

        months = response.data["months"]
        assert len(months) == 12
        assert months[0]["month"] == date(past_year, 1, 1).isoformat()
        assert months[-1]["month"] == date(past_year, 12, 1).isoformat()
        assert months[5]["total"] == 75.0  # June

    def test_year_param_for_the_current_year_stops_at_the_current_month(self, owner, car):
        today = timezone.localdate()

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get(f"/api/v1/expenses/analytics/?year={today.year}")

        months = response.data["months"]
        assert len(months) == today.month
        assert months[-1]["month"] == today.replace(day=1).isoformat()

    def test_year_param_for_a_future_year_returns_no_months(self, owner, car):
        future_year = timezone.localdate().year + 1

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get(f"/api/v1/expenses/analytics/?year={future_year}")

        assert response.data["months"] == []
        assert response.data["grand_total"] == 0

    def test_months_param_still_returns_a_trailing_window(self, owner, car):
        """Explicit ?months= (used by the reports page's month picker) keeps
        the old rolling-window behavior rather than snapping to a calendar
        year — it's an intentional override, not replaced by #58."""
        today = timezone.localdate()
        Expense.objects.create(car=car, category="fuel", amount=40, expense_date=today)

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/?months=3")

        months = response.data["months"]
        assert len(months) == 3
        assert months[-1]["month"] == today.replace(day=1).isoformat()

    def test_months_before_signup_are_not_zero_filled(self, owner, car):
        """See #60 — a wide ?months= window (the reports page uses 24)
        shouldn't manufacture $0 "ghost" report entries for months before
        the account existed."""
        today = timezone.localdate()
        owner.date_joined = timezone.now() - relativedelta(months=2)
        owner.save(update_fields=["date_joined"])
        Expense.objects.create(car=car, category="fuel", amount=50, expense_date=today)

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/?months=24")

        months = response.data["months"]
        earliest = date.fromisoformat(months[0]["month"])
        assert earliest >= timezone.localtime(owner.date_joined).date().replace(day=1)
        assert len(months) <= 3  # join month, the month after, and this month

    def test_real_backdated_data_before_signup_still_shows(self, owner, car):
        """A deliberately backdated entry (e.g. a historical service logged
        after signing up) is real data, not a manufactured ghost month —
        the #60 guard only suppresses zero-filled months, never real ones."""
        owner.date_joined = timezone.now() - relativedelta(days=1)
        owner.save(update_fields=["date_joined"])
        # Well within the ?months=24 window (unlike the signup date) — this
        # test is about the signup-date guard, not the window's own edge.
        old_date = timezone.localdate() - relativedelta(months=6)
        Expense.objects.create(car=car, category="fuel", amount=75, expense_date=old_date)

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/?months=24")

        months = {m["month"]: m for m in response.data["months"]}
        assert months[old_date.replace(day=1).isoformat()]["total"] == 75.0

    def test_default_calendar_year_window_also_respects_signup_date(self, owner, car):
        """The #60 guard applies to the default calendar-year window too
        (see #58), not just an explicit ?months=."""
        today = timezone.localdate()
        owner.date_joined = timezone.now().replace(day=1)
        owner.save(update_fields=["date_joined"])

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/")

        months = response.data["months"]
        assert len(months) == 1
        assert months[0]["month"] == today.replace(day=1).isoformat()


@pytest.mark.django_db
class TestExpenseMonthlyReport:

    def test_breakdown_by_category_and_car(self, owner, car):
        other_car = Car.objects.create(owner=owner, make="Honda", model="Civic")
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))
        Expense.objects.create(car=car, category="garage_visit", amount=50, expense_date=date(2026, 5, 20))
        Expense.objects.create(car=other_car, category="fuel", amount=30, expense_date=date(2026, 5, 15))
        Expense.objects.create(car=car, category="fuel", amount=999, expense_date=date(2026, 4, 1))  # different month

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/2026-5/")

        assert response.status_code == 200
        assert response.data["month_label"] == "May 2026"
        assert response.data["total"] == 180.0
        assert response.data["count"] == 3
        by_category = {row["category"]: row["total"] for row in response.data["by_category"]}
        assert by_category == {"fuel": 130.0, "garage_visit": 50.0}
        assert len(response.data["by_car"]) == 2

    def test_converts_totals_and_category_breakdown_to_the_owners_currency(self, owner, car, rates):
        owner.currency = "USD"
        owner.save(update_fields=["currency"])
        Expense.objects.create(car=car, category="fuel", amount=3700, currency="UGX", expense_date=date(2026, 5, 5))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/2026-5/")

        assert round(response.data["total"], 2) == 1.0
        assert response.data["currency"] == "USD"
        assert round(response.data["by_category"][0]["total"], 2) == 1.0

    def test_report_carries_the_owners_currency(self, owner, car):
        """See #40 — the report is the one source of truth for currency across
        the in-app view, PDF, and email digest, so it rides along on the same
        dict rather than being looked up separately by each renderer."""
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))
        owner.currency = "KES"
        owner.save(update_fields=["currency"])

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/2026-5/")

        assert response.data["currency"] == "KES"

    def test_report_currency_is_blank_when_unset(self, owner, car):
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/2026-5/")

        assert response.data["currency"] == ""

    def test_change_vs_previous_month(self, owner, car):
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 4, 10))
        Expense.objects.create(car=car, category="fuel", amount=150, expense_date=date(2026, 5, 10))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/2026-5/")

        assert response.data["previous_month_total"] == 100.0
        assert response.data["change_vs_previous_month"] == 50.0
        assert response.data["change_percent_vs_previous_month"] == 50.0

    def test_other_owners_expenses_excluded(self, owner, car):
        other = User.objects.create_user(email="other-report@example.com", password="str0ng-pass-123")
        other_car = Car.objects.create(owner=other, make="Honda", model="Civic")
        Expense.objects.create(car=other_car, category="fuel", amount=999, expense_date=date(2026, 5, 1))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/2026-5/")

        assert response.data["total"] == 0.0
        assert response.data["by_category"] == []

    def test_pdf_endpoint_returns_a_pdf(self, owner, car):
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/2026-5/pdf/")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"] == 'attachment; filename="glavbox-expenses-2026-05.pdf"'
        assert response.content.startswith(b"%PDF")

    def test_requires_authentication(self, car):
        client = APIClient()
        response = client.get("/api/v1/expenses/reports/2026-5/")

        assert response.status_code == 401

    def test_rejects_invalid_month(self, owner):
        client = APIClient()
        client.force_authenticate(owner)

        response = client.get("/api/v1/expenses/reports/2026-13/")

        assert response.status_code == 400

    def test_pdf_endpoint_rejects_invalid_month(self, owner):
        client = APIClient()
        client.force_authenticate(owner)

        response = client.get("/api/v1/expenses/reports/2026-0/pdf/")

        assert response.status_code == 400

    def test_rejects_january_of_minyear(self, owner):
        """
        build_monthly_report computes the previous month as (year - 1, 12)
        for month == 1, and MINYEAR - 1 underflows datetime's range — this
        boundary must be rejected before it ever reaches that calculation.
        """
        client = APIClient()
        client.force_authenticate(owner)

        response = client.get("/api/v1/expenses/reports/1-1/")

        assert response.status_code == 400


@pytest.mark.django_db
class TestExpenseAllTimeReport:

    def test_aggregates_everything_ever_logged_across_cars(self, owner, car):
        other_car = Car.objects.create(owner=owner, make="Honda", model="Civic")
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2020, 1, 10))
        Expense.objects.create(car=car, category="garage_visit", amount=50, expense_date=date(2023, 6, 20))
        Expense.objects.create(car=other_car, category="fuel", amount=30, expense_date=date(2026, 5, 15))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/all-time/")

        assert response.status_code == 200
        assert response.data["month_label"] == "All-time"
        assert response.data["total"] == 180.0
        assert response.data["count"] == 3
        assert response.data["since"] == "January 2020"
        by_category = {row["category"]: row["total"] for row in response.data["by_category"]}
        assert by_category == {"fuel": 130.0, "garage_visit": 50.0}
        assert len(response.data["by_car"]) == 2

    def test_no_previous_period_comparison(self, owner, car):
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2020, 1, 10))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/all-time/")

        assert response.data["previous_month_total"] is None
        assert response.data["change_vs_previous_month"] is None
        assert response.data["change_percent_vs_previous_month"] is None

    def test_no_expenses_yet(self, owner, car):
        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/all-time/")

        assert response.data["total"] == 0.0
        assert response.data["count"] == 0
        assert response.data["since"] is None
        assert response.data["by_category"] == []

    def test_other_owners_expenses_excluded(self, owner, car):
        other = User.objects.create_user(email="other-all-time@example.com", password="str0ng-pass-123")
        other_car = Car.objects.create(owner=other, make="Honda", model="Civic")
        Expense.objects.create(car=other_car, category="fuel", amount=999, expense_date=date(2020, 1, 1))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/all-time/")

        assert response.data["total"] == 0.0

    def test_pdf_endpoint_returns_a_pdf(self, owner, car):
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2020, 1, 10))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/reports/all-time/pdf/")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"] == 'attachment; filename="glavbox-expenses-all-time.pdf"'
        assert response.content.startswith(b"%PDF")

    def test_requires_authentication(self, car):
        client = APIClient()
        response = client.get("/api/v1/expenses/reports/all-time/")

        assert response.status_code == 401


@pytest.mark.django_db
class TestMonthlyExpenseReportTask:

    def test_sends_digest_only_to_users_with_expenses_last_month(self, owner, car):
        from django.core import mail

        from tasks import send_monthly_expense_reports_task

        prev_year, prev_month = previous_month()
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(prev_year, prev_month, 5))

        quiet_owner = User.objects.create_user(email="quiet@example.com", password="str0ng-pass-123")
        quiet_owner.is_email_verified = True
        quiet_owner.save(update_fields=["is_email_verified"])
        Car.objects.create(owner=quiet_owner, make="Mazda", model="3")

        send_monthly_expense_reports_task()

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [owner.email]

    def test_skips_inactive_users(self, owner, car):
        from django.core import mail

        from tasks import send_monthly_expense_reports_task

        prev_year, prev_month = previous_month()
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(prev_year, prev_month, 5))
        User.objects.filter(pk=owner.pk).update(is_active=False)

        send_monthly_expense_reports_task()

        assert len(mail.outbox) == 0

    def test_email_task_skips_zero_expense_user(self, owner):
        from django.core import mail

        from tasks import send_monthly_expense_report_email_task

        send_monthly_expense_report_email_task(user_id=owner.pk, year=2026, month=5)

        assert len(mail.outbox) == 0

    def test_successful_send_confirms_the_delivery(self, owner, car):
        from expenses.models import MonthlyExpenseReportDelivery
        from tasks import send_monthly_expense_report_email_task

        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))

        send_monthly_expense_report_email_task(user_id=owner.pk, year=2026, month=5)

        delivery = MonthlyExpenseReportDelivery.objects.get(user=owner, year=2026, month=5)
        assert delivery.sent_at is not None

    def test_does_not_resend_once_confirmed(self, owner, car):
        from django.core import mail

        from expenses.models import MonthlyExpenseReportDelivery
        from tasks import send_monthly_expense_report_email_task

        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))
        MonthlyExpenseReportDelivery.objects.create(user=owner, year=2026, month=5, sent_at=timezone.now())

        send_monthly_expense_report_email_task(user_id=owner.pk, year=2026, month=5)

        assert len(mail.outbox) == 0

    def test_does_not_send_while_another_claim_is_still_live(self, owner, car):
        """
        Regression: two concurrent/redelivered executions for the same
        (user, year, month) must not both send. A fresh, unconfirmed claim
        (queued_at within the lease window) means another execution is
        presumed still in flight, so this one backs off rather than racing it.
        """
        from django.core import mail

        from expenses.models import MonthlyExpenseReportDelivery
        from tasks import send_monthly_expense_report_email_task

        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))
        MonthlyExpenseReportDelivery.objects.create(user=owner, year=2026, month=5, queued_at=timezone.now())

        send_monthly_expense_report_email_task(user_id=owner.pk, year=2026, month=5)

        assert len(mail.outbox) == 0

    def test_reclaims_a_stale_unconfirmed_claim_and_sends(self, owner, car):
        """
        A claim whose send never confirmed (crash, prior failure) goes stale
        after Constants.REMINDER_CLAIM_LEASE_HOURS and must be retried, not
        left permanently unsent.
        """
        from datetime import timedelta

        from django.core import mail

        from expenses.models import MonthlyExpenseReportDelivery
        from tasks import send_monthly_expense_report_email_task
        from utils import Constants

        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))
        stale = timezone.now() - timedelta(hours=Constants.REMINDER_CLAIM_LEASE_HOURS, minutes=1)
        MonthlyExpenseReportDelivery.objects.create(user=owner, year=2026, month=5, queued_at=stale)

        send_monthly_expense_report_email_task(user_id=owner.pk, year=2026, month=5)

        assert len(mail.outbox) == 1
        delivery = MonthlyExpenseReportDelivery.objects.get(user=owner, year=2026, month=5)
        assert delivery.sent_at is not None

    def test_sweep_excludes_confirmed_deliveries_but_retries_unconfirmed_ones(self, owner, car):
        from django.core import mail

        from expenses.models import MonthlyExpenseReportDelivery
        from tasks import send_monthly_expense_reports_task

        prev_year, prev_month = previous_month()
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(prev_year, prev_month, 5))
        MonthlyExpenseReportDelivery.objects.create(
            user=owner, year=prev_year, month=prev_month, sent_at=timezone.now()
        )

        result = send_monthly_expense_reports_task()

        assert result == "Queued 0 monthly expense report email(s)"

        # A previously-failed (unconfirmed) claim for a *different* user is
        # still open to retry on a re-run.
        other = User.objects.create_user(email="retry-me@example.com", password="str0ng-pass-123")
        other.is_email_verified = True
        other.save(update_fields=["is_email_verified"])
        other_car = Car.objects.create(owner=other, make="Mazda", model="3")
        Expense.objects.create(car=other_car, category="fuel", amount=50, expense_date=date(prev_year, prev_month, 5))
        MonthlyExpenseReportDelivery.objects.create(
            user=other, year=prev_year, month=prev_month, queued_at=timezone.now() - timezone.timedelta(hours=999)
        )

        result = send_monthly_expense_reports_task()

        assert result == "Queued 1 monthly expense report email(s)"
        assert mail.outbox[0].to == [other.email]

    def test_sweep_does_not_exclude_users_whose_deliveries_are_for_other_periods(self, owner, car):
        """
        Regression: a naive `.exclude(deliveries__year=Y, deliveries__month=M)`
        on a reverse FK does not require both conditions to hold on the same
        related row — a delivery matching `year` and a *different* delivery
        matching `month` both count, independently. A user confirmed for a
        different month in the same year (or the same month in a different
        year) must still be queued for the target period.
        """
        from expenses.models import MonthlyExpenseReportDelivery
        from tasks import send_monthly_expense_reports_task

        prev_year, prev_month = previous_month()
        other_month = 1 if prev_month != 1 else 2
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(prev_year, prev_month, 5))
        # Matches `year` alone (different month) ...
        MonthlyExpenseReportDelivery.objects.create(
            user=owner, year=prev_year, month=other_month, sent_at=timezone.now()
        )
        # ... and matches `month` alone (different year) — together these
        # would satisfy an independently-applied year/month exclude() even
        # though neither row is a delivery for (prev_year, prev_month).
        other_year = prev_year - 1
        MonthlyExpenseReportDelivery.objects.create(
            user=owner, year=other_year, month=prev_month, sent_at=timezone.now()
        )

        result = send_monthly_expense_reports_task()

        assert result == "Queued 1 monthly expense report email(s)"

    def test_month_check_constraint_rejects_out_of_range_month(self, owner):
        from django.db import IntegrityError

        from expenses.models import MonthlyExpenseReportDelivery

        with pytest.raises(IntegrityError):
            MonthlyExpenseReportDelivery.objects.create(user=owner, year=2026, month=13)


@pytest.mark.django_db
class TestRefreshExchangeRatesTask:
    """See #40 — the daily FX-rate fetch that powers currency conversion."""

    def test_stores_a_rate_row_for_each_supported_currency_present_in_the_response(self, monkeypatch):
        from tasks import refresh_exchange_rates_task

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"rates": {"UGX": 3700.0, "KES": 129.0, "USD": 1.0}}

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: FakeResponse())

        refresh_exchange_rates_task()

        today = timezone.localdate()
        ugx_rate = ExchangeRate.objects.get(date=today, currency="UGX").rate_to_usd
        assert round(ugx_rate, 6) == round(Decimal("1") / Decimal("3700"), 6)

    def test_skips_currencies_missing_from_the_response(self, monkeypatch):
        from tasks import refresh_exchange_rates_task

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"rates": {"USD": 1.0}}  # no UGX today

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: FakeResponse())

        refresh_exchange_rates_task()

        assert not ExchangeRate.objects.filter(currency="UGX").exists()

    def test_a_failed_fetch_does_not_raise(self, monkeypatch):
        from tasks import refresh_exchange_rates_task

        def failing_get(*args, **kwargs):
            raise ConnectionError("network down")

        monkeypatch.setattr("requests.get", failing_get)

        result = refresh_exchange_rates_task()

        assert "Failed" in result
        assert not ExchangeRate.objects.exists()

    def test_a_successful_refresh_invalidates_the_cached_rates(self, monkeypatch):
        from tasks import refresh_exchange_rates_task
        from utils import Cache
        from utils.Currency import load_latest_rates

        ExchangeRate.objects.create(date=date(2026, 1, 1), currency="USD", rate_to_usd=Decimal("1"))
        assert load_latest_rates() == {"USD": Decimal("1")}  # warms the cache

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"rates": {"USD": 1.0, "UGX": 3700.0}}

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: FakeResponse())
        refresh_exchange_rates_task()

        assert Cache.get_exchange_rates() is None
        assert "UGX" in load_latest_rates()

    def test_a_failed_fetch_does_not_invalidate_the_cached_rates(self, monkeypatch):
        from tasks import refresh_exchange_rates_task
        from utils import Cache
        from utils.Currency import load_latest_rates

        ExchangeRate.objects.create(date=date(2026, 1, 1), currency="USD", rate_to_usd=Decimal("1"))
        load_latest_rates()  # warms the cache

        monkeypatch.setattr("requests.get", lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("down")))
        refresh_exchange_rates_task()

        assert Cache.get_exchange_rates() == {"USD": Decimal("1")}
