from datetime import date

import pytest
from dateutil.relativedelta import relativedelta

from accounts.models import User
from cars.models import Car
from reminders.engine import evaluate_reminder
from reminders.models import Reminder
from reminders.serializers import ReminderCreateSerializer, ReminderEditSerializer
from utils import Constants
from utils.Exception import CustomValidation


@pytest.fixture
def car(db):
    owner = User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")
    return Car.objects.create(owner=owner, make="Toyota", model="Corolla", current_odometer_km=40000)


@pytest.mark.django_db
class TestReminderIntervals:

    def test_next_due_computed_from_baseline_and_intervals(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Engine oil & filter change",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
            interval_km=5000, interval_months=6,
            baseline_odometer_km=40000, baseline_date=date(2026, 1, 10),
        )
        assert reminder.next_due_odometer_km == 45000
        assert reminder.next_due_date == date(2026, 7, 10)

    def test_mileage_only_ignores_date(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Spark plug replacement",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            interval_km=30000, baseline_odometer_km=40000,
        )
        assert reminder.next_due_odometer_km == 70000
        assert reminder.next_due_date is None

    def test_date_only_ignores_mileage(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Car insurance renewal",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE,
            interval_months=12, baseline_date=date(2026, 1, 1),
        )
        assert reminder.next_due_date == date(2027, 1, 1)
        assert reminder.next_due_odometer_km is None


@pytest.mark.django_db
class TestReminderStatus:

    def test_status_overdue_when_km_threshold_passed(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Brake fluid change",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            interval_km=5000, baseline_odometer_km=30000,
        )
        car.current_odometer_km = 40000  # past 35,000
        result = evaluate_reminder(reminder)
        assert result["status"] == Constants.REMINDER_STATUS_OVERDUE

    def test_status_overdue_when_date_passed(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Vehicle inspection",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE,
            interval_months=6, baseline_date=date.today() - relativedelta(months=7),
        )
        result = evaluate_reminder(reminder)
        assert result["status"] == Constants.REMINDER_STATUS_OVERDUE

    def test_status_due_soon_within_km_window(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Tyre rotation",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            interval_km=5000, baseline_odometer_km=40000,
        )
        car.current_odometer_km = 44700  # 300 km to go
        result = evaluate_reminder(reminder)
        assert result["status"] == Constants.REMINDER_STATUS_DUE_SOON

    def test_status_ok_when_far_from_threshold(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Timing belt/chain replacement",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
            interval_km=100000, interval_months=60,
            baseline_odometer_km=40000, baseline_date=date.today(),
        )
        result = evaluate_reminder(reminder)
        assert result["status"] == Constants.REMINDER_STATUS_OK

    def test_progress_percent_uses_worse_of_km_and_date(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Engine oil & filter change",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
            interval_km=10000, interval_months=12,
            baseline_odometer_km=40000, baseline_date=date.today() - relativedelta(months=6),
        )
        car.current_odometer_km = 41000  # 10% of the km leg elapsed
        result = evaluate_reminder(reminder)
        # date leg (6 of 12 months = 50%) is worse than km leg (10%)
        assert result["progress_percent"] == pytest.approx(50, abs=2)

    def test_progress_percent_clamped_0_100(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Cabin air filter replacement",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            interval_km=5000, baseline_odometer_km=30000,
        )
        car.current_odometer_km = 100000  # way past due
        result = evaluate_reminder(reminder)
        assert result["progress_percent"] == 100


@pytest.mark.django_db
class TestReminderSerializers:

    def test_create_requires_interval_for_tracking_method(self, car):
        serializer = ReminderCreateSerializer(data={
            "car": car.pk, "title": "Custom reminder",
            "tracking_method": Constants.REMINDER_TRACKING_METHOD_MILEAGE,
        })
        with pytest.raises(CustomValidation):
            serializer.is_valid()

    def test_create_defaults_baseline_from_car_and_today(self, car):
        serializer = ReminderCreateSerializer(data={
            "car": car.pk, "title": "Engine oil & filter change",
            "tracking_method": Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            "interval_km": 5000,
        })
        assert serializer.is_valid(), serializer.errors
        reminder = serializer.save()
        assert reminder.baseline_odometer_km == car.current_odometer_km
        assert reminder.next_due_odometer_km == car.current_odometer_km + 5000

    def test_edit_backfills_baseline_when_switching_tracking_method(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Windshield wiper blade replacement",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE,
            interval_months=12, baseline_date=date.today(),
        )
        serializer = ReminderEditSerializer(
            reminder, data={"tracking_method": Constants.REMINDER_TRACKING_METHOD_MILEAGE, "interval_km": 15000},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.baseline_odometer_km == car.current_odometer_km
        assert updated.next_due_odometer_km == car.current_odometer_km + 15000

    def test_edit_switching_tracking_method_without_interval_raises(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Windshield wiper blade replacement",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE,
            interval_months=12, baseline_date=date.today(),
        )
        serializer = ReminderEditSerializer(
            reminder, data={"tracking_method": Constants.REMINDER_TRACKING_METHOD_MILEAGE},
            partial=True,
        )
        with pytest.raises(CustomValidation):
            serializer.is_valid()

    def test_edit_switching_tracking_method_clears_stale_threshold(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Engine oil & filter change",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
            interval_km=5000, interval_months=6,
            baseline_odometer_km=40000, baseline_date=date.today(),
        )
        assert reminder.next_due_odometer_km is not None
        assert reminder.next_due_date is not None

        serializer = ReminderEditSerializer(
            reminder, data={"tracking_method": Constants.REMINDER_TRACKING_METHOD_DATE},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        # Switching to date-only must drop the now-irrelevant km threshold,
        # even though the old interval_km/baseline_odometer_km are still stored.
        assert updated.next_due_odometer_km is None
        assert updated.next_due_date is not None
