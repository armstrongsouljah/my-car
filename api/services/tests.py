from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import Car
from expenses.models import Expense
from reminders.catalog import OIL_CHANGE_KEY
from reminders.models import Reminder
from services.models import ServiceRecord
from services.reminders import build_inspection_reminder, build_service_reminder
from utils import Constants


@pytest.fixture
def car(db):
    owner = User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")
    return Car.objects.create(owner=owner, make="Toyota", model="Corolla", current_odometer_km=40000)


@pytest.fixture
def client():
    return APIClient()


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

    def test_zero_cost_still_creates_and_keeps_the_expense(self, car):
        """A $0 service (e.g. covered under warranty) is a known cost, unlike
        an unset one — it must not be treated the same as no cost at all."""
        record = ServiceRecord.objects.create(
            car=car, odometer_km=41000, interval_km=5000, cost="0.00",
        )
        expense = Expense.objects.get(service_record=record)
        assert str(expense.amount) == "0.00"

        record.save()
        assert Expense.objects.filter(service_record=record).exists()

    def test_deleting_service_deletes_its_expense(self, car):
        record = ServiceRecord.objects.create(
            car=car, odometer_km=41000, interval_km=5000, cost="150.00",
        )
        expense_id = Expense.objects.get(service_record=record).id
        record.delete()
        assert not Expense.objects.filter(id=expense_id).exists()


@pytest.mark.django_db
class TestServiceReminderSync:

    def test_oil_change_creates_matching_catalog_reminder(self, car):
        ServiceRecord.objects.create(
            car=car, service_type=Constants.SERVICE_TYPE_OIL_CHANGE,
            odometer_km=41000, service_date=date(2026, 3, 1),
            interval_km=6000, interval_months=7,
        )
        reminder = Reminder.objects.get(car=car, catalog_key=OIL_CHANGE_KEY)
        assert reminder.baseline_odometer_km == 41000
        assert reminder.baseline_date == date(2026, 3, 1)
        assert reminder.interval_km == 6000
        assert reminder.interval_months == 7
        assert reminder.title == "Engine oil & filter change"

    def test_other_service_types_do_not_touch_the_catalog_reminder(self, car):
        ServiceRecord.objects.create(
            car=car, service_type=Constants.SERVICE_TYPE_BRAKES, odometer_km=41000,
        )
        assert not Reminder.objects.filter(car=car, catalog_key=OIL_CHANGE_KEY).exists()

    def test_updating_the_service_record_moves_the_reminder_baseline(self, car):
        record = ServiceRecord.objects.create(
            car=car, service_type=Constants.SERVICE_TYPE_OIL_CHANGE,
            odometer_km=41000, service_date=date(2026, 3, 1), interval_km=5000,
        )
        record.odometer_km = 42500
        record.service_date = date(2026, 4, 1)
        record.save()

        reminder = Reminder.objects.get(car=car, catalog_key=OIL_CHANGE_KEY)
        assert reminder.baseline_odometer_km == 42500
        assert reminder.baseline_date == date(2026, 4, 1)

    def test_customized_interval_is_not_clobbered(self, car):
        ServiceRecord.objects.create(
            car=car, service_type=Constants.SERVICE_TYPE_OIL_CHANGE,
            odometer_km=41000, interval_km=5000,
        )
        reminder = Reminder.objects.get(car=car, catalog_key=OIL_CHANGE_KEY)
        reminder.interval_km = 8000  # owner deliberately customizes away from the default/synced value
        reminder.save()

        ServiceRecord.objects.create(
            car=car, service_type=Constants.SERVICE_TYPE_OIL_CHANGE,
            odometer_km=46000, interval_km=5000,
        )
        reminder.refresh_from_db()
        assert reminder.interval_km == 8000
        assert reminder.baseline_odometer_km == 46000

    def test_editing_an_older_record_does_not_move_baseline_backwards(self, car):
        older = ServiceRecord.objects.create(
            car=car, service_type=Constants.SERVICE_TYPE_OIL_CHANGE,
            odometer_km=40000, service_date=date(2026, 1, 1),
        )
        ServiceRecord.objects.create(
            car=car, service_type=Constants.SERVICE_TYPE_OIL_CHANGE,
            odometer_km=45000, service_date=date(2026, 6, 1),
        )

        older.garage_name = "Joe's Garage"
        older.save()

        reminder = Reminder.objects.get(car=car, catalog_key=OIL_CHANGE_KEY)
        assert reminder.baseline_odometer_km == 45000
        assert reminder.baseline_date == date(2026, 6, 1)


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


@pytest.mark.django_db
class TestRemindersView:

    def test_hides_ok_reminders(self, car, client):
        client.force_authenticate(car.owner)
        response = client.get(reverse("service-reminders"))
        assert response.status_code == 200
        assert response.data[0]["reminders"] == []

    def test_surfaces_due_reminders(self, car, client):
        ServiceRecord.objects.create(
            car=car, odometer_km=40000,
            service_date=date.today() - relativedelta(months=7),
            interval_km=5000, interval_months=6,
        )
        client.force_authenticate(car.owner)
        response = client.get(reverse("service-reminders"))
        kinds = [r["kind"] for r in response.data[0]["reminders"]]
        assert kinds == ["service"]

    def test_suppresses_service_reminder_when_oil_change_reminder_exists(self, car, client):
        ServiceRecord.objects.create(
            car=car, odometer_km=40000,
            service_date=date.today() - relativedelta(months=7),
            interval_km=5000, interval_months=6,
        )
        Reminder.objects.create(
            car=car, catalog_key=OIL_CHANGE_KEY, title="Engine oil & filter change",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            interval_km=5000, baseline_odometer_km=40000,
        )
        client.force_authenticate(car.owner)
        response = client.get(reverse("service-reminders"))
        assert response.data[0]["reminders"] == []

    def test_exposes_make_model_and_plate_separately(self, car, client):
        car.registration_number = "ABC123"
        car.save()
        client.force_authenticate(car.owner)
        response = client.get(reverse("service-reminders"))
        entry = response.data[0]
        assert entry["make"] == "Toyota"
        assert entry["model"] == "Corolla"
        assert entry["registration_number"] == "ABC123"
        assert "car" not in entry
