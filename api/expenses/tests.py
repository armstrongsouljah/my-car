from datetime import date

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import Car
from expenses.models import Expense


def previous_month():
    """Year/month one calendar month before "today" — mirrors the task's own calculation."""
    today = timezone.localdate()
    return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)


@pytest.fixture
def owner(db):
    user = User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    return user


@pytest.fixture
def car(owner):
    return Car.objects.create(owner=owner, make="Toyota", model="Corolla")


@pytest.mark.django_db
class TestExpenseAnalytics:

    def test_month_on_month_totals_and_change(self, owner, car):
        Expense.objects.create(car=car, category="fuel", amount=100, expense_date=date(2026, 5, 10))
        Expense.objects.create(car=car, category="garage_visit", amount=50, expense_date=date(2026, 5, 20))
        Expense.objects.create(car=car, category="fuel", amount=200, expense_date=date(2026, 6, 5))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/")

        assert response.status_code == 200
        months = response.data["months"]
        assert months[0]["total"] == 150.0
        assert months[0]["by_category"] == {"fuel": 100.0, "garage_visit": 50.0}
        assert months[1]["total"] == 200.0
        assert months[1]["change_vs_previous_month"] == 50.0
        assert response.data["grand_total"] == 350.0

    def test_other_owners_expenses_excluded(self, owner, car, db):
        other = User.objects.create_user(email="other@example.com", password="str0ng-pass-123")
        other_car = Car.objects.create(owner=other, make="Honda", model="Civic")
        Expense.objects.create(car=other_car, category="fuel", amount=999, expense_date=date(2026, 6, 1))
        Expense.objects.create(car=car, category="fuel", amount=10, expense_date=date(2026, 6, 1))

        client = APIClient()
        client.force_authenticate(owner)
        response = client.get("/api/v1/expenses/analytics/")

        assert response.data["grand_total"] == 10.0


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
