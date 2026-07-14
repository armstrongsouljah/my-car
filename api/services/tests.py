from datetime import date

import pytest
from dateutil.relativedelta import relativedelta

from accounts.models import User
from cars.models import Car
from services.models import ServiceRecord
from services.reminders import build_service_reminder
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
