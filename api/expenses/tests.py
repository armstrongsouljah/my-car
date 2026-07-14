from datetime import date

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import Car
from expenses.models import Expense


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
