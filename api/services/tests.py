from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from accounts.models import User
from cars.models import Car
from expenses.models import Expense
from services.models import ServiceRecord
from services.reminders import build_inspection_reminder, build_service_reminder
from utils import Constants


@pytest.fixture
def car(db):
    owner = User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")
    return Car.objects.create(owner=owner, make="Toyota", model="Corolla", current_odometer_km=40000)


@pytest.mark.django_db
class TestServiceIntervals:

    def test_next_due_computed_from_intervals(self, car):
        record = ServiceRecord.objects.create(
            car=car, odometer_km=40000, service_date=date(2026, 1, 10),
            interval_km=5000, interval_months=6,
        )
        assert record.next_due_odometer_km == 45000
        assert record.next_due_date == date(2026, 7, 10)

    def test_service_moves_car_odometer_forward(self, car):
        ServiceRecord.objects.create(car=car, odometer_km=41000, interval_km=5000)
        car.refresh_from_db()
        assert car.current_odometer_km == 41000

    def test_km_threshold_trips_first(self, car):
        """10,000 km or 12 months — km runs out first."""
        ServiceRecord.objects.create(
            car=car, odometer_km=40000, service_date=date.today(),
            interval_km=10000, interval_months=12,
        )
        car.current_odometer_km = 50100  # past 50,000
        reminder = build_service_reminder(car)
        assert reminder["status"] == Constants.REMINDER_STATUS_OVERDUE

    def test_date_threshold_trips_first(self, car):
        """5,000 km or 6 months — the 6 months elapse before the km do."""
        ServiceRecord.objects.create(
            car=car, odometer_km=40000,
            service_date=date.today() - relativedelta(months=7),
            interval_km=5000, interval_months=6,
        )
        reminder = build_service_reminder(car)
        assert reminder["status"] == Constants.REMINDER_STATUS_OVERDUE

    def test_due_soon_within_km_window(self, car):
        ServiceRecord.objects.create(
            car=car, odometer_km=40000, service_date=date.today(),
            interval_km=5000, interval_months=12,
        )
        car.current_odometer_km = 44700  # 300 km to go
        reminder = build_service_reminder(car)
        assert reminder["status"] == Constants.REMINDER_STATUS_DUE_SOON

    def test_ok_when_far_from_both_thresholds(self, car):
        ServiceRecord.objects.create(
            car=car, odometer_km=40000, service_date=date.today(),
            interval_km=10000, interval_months=12,
        )
        reminder = build_service_reminder(car)
        assert reminder["status"] == Constants.REMINDER_STATUS_OK


@pytest.mark.django_db
class TestServiceExpenseSync:

    def test_costed_service_creates_linked_expense(self, car):
        record = ServiceRecord.objects.create(
            car=car, odometer_km=41000, service_date=date(2026, 3, 1),
            interval_km=5000, cost="150.00", garage_name="Joe's Garage",
            description="Oil + filter change",
        )
        expense = Expense.objects.get(service_record=record)
        assert expense.car_id == car.id
        assert expense.category == Constants.EXPENSE_CATEGORY_GARAGE
        assert str(expense.amount) == "150.00"
        assert expense.expense_date == date(2026, 3, 1)
        assert expense.vendor == "Joe's Garage"
        assert expense.description == "Oil + filter change"
        assert expense.odometer_km == 41000

    def test_updating_cost_updates_the_same_expense(self, car):
        record = ServiceRecord.objects.create(
            car=car, odometer_km=41000, interval_km=5000, cost="150.00",
        )
        expense_id = Expense.objects.get(service_record=record).id

        record.cost = "175.00"
        record.save()

        assert Expense.objects.filter(service_record=record).count() == 1
        expense = Expense.objects.get(service_record=record)
        assert expense.id == expense_id
        assert str(expense.amount) == "175.00"

    def test_clearing_cost_removes_the_expense(self, car):
        record = ServiceRecord.objects.create(
            car=car, odometer_km=41000, interval_km=5000, cost="150.00",
        )
        record.cost = None
        record.save()
        assert not Expense.objects.filter(service_record=record).exists()

    def test_no_cost_does_not_create_an_expense(self, car):
        record = ServiceRecord.objects.create(car=car, odometer_km=41000, interval_km=5000)
        assert not Expense.objects.filter(service_record=record).exists()

    def test_deleting_service_deletes_its_expense(self, car):
        record = ServiceRecord.objects.create(
            car=car, odometer_km=41000, interval_km=5000, cost="150.00",
        )
        expense_id = Expense.objects.get(service_record=record).id
        record.delete()
        assert not Expense.objects.filter(id=expense_id).exists()


@pytest.mark.django_db
class TestNewCarGracePeriod:

    def test_no_service_record_is_ok_within_grace_period(self, car):
        reminder = build_service_reminder(car)
        assert reminder["status"] == Constants.REMINDER_STATUS_OK

    def test_no_service_record_is_due_soon_after_grace_period(self, car):
        old = timezone.now() - timedelta(days=Constants.REMINDER_NEW_CAR_GRACE_DAYS + 1)
        Car.objects.filter(pk=car.pk).update(created_at=old)
        car.refresh_from_db()
        reminder = build_service_reminder(car)
        assert reminder["status"] == Constants.REMINDER_STATUS_DUE_SOON

    def test_no_inspection_is_ok_within_grace_period(self, car):
        reminder = build_inspection_reminder(car)
        assert reminder["status"] == Constants.REMINDER_STATUS_OK
