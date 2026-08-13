from datetime import date
from unittest.mock import patch

import pytest
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import Car
from reminders.catalog import get_reminder_catalog
from reminders.engine import evaluate_reminder
from reminders.models import Reminder
from reminders.serializers import ReminderCreateSerializer, ReminderEditSerializer
from utils import Constants
from utils.Exception import CustomValidation


@pytest.fixture
def car(db):
    owner = User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")
    return Car.objects.create(owner=owner, make="Toyota", model="Corolla", current_odometer_km=40000)


@pytest.fixture
def client():
    return APIClient()


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


@pytest.mark.django_db
class TestReminderListCaching:

    def _create(self, car, **overrides):
        fields = dict(
            car=car, title="Oil change",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            interval_km=5000, baseline_odometer_km=car.current_odometer_km,
        )
        fields.update(overrides)
        return Reminder.objects.create(**fields)

    def test_unfiltered_list_is_cached_across_requests(self, car, client):
        client.force_authenticate(car.owner)
        first = client.get(reverse("reminder-list-create"))

        # Bypasses the API's own invalidation hook — proves the second
        # request is served from cache, not recomputed.
        self._create(car)

        second = client.get(reverse("reminder-list-create"))
        assert second.data == first.data

    def test_filtered_request_bypasses_the_cache(self, car, client):
        client.force_authenticate(car.owner)
        client.get(reverse("reminder-list-create"))  # warms the unfiltered cache

        self._create(car)

        filtered = client.get(reverse("reminder-list-create"), {"car": str(car.pk)})
        results = filtered.data.get("results", filtered.data)
        assert len(results) == 1

    def test_creating_a_reminder_invalidates_the_cache(self, car, client):
        client.force_authenticate(car.owner)
        client.get(reverse("reminder-list-create"))  # warm

        resp = client.post(reverse("reminder-list-create"), {
            "car": str(car.pk), "title": "Oil change",
            "tracking_method": Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            "interval_km": 5000,
        }, format="json")
        assert resp.status_code == 201

        listing = client.get(reverse("reminder-list-create"))
        results = listing.data.get("results", listing.data)
        assert len(results) == 1

    def test_editing_a_reminder_invalidates_the_cache(self, car, client):
        reminder = self._create(car)
        client.force_authenticate(car.owner)
        client.get(reverse("reminder-list-create"))  # warm

        resp = client.patch(reverse("reminder-detail", args=[reminder.pk]), {"title": "New title"}, format="json")
        assert resp.status_code == 200

        listing = client.get(reverse("reminder-list-create"))
        results = listing.data.get("results", listing.data)
        assert results[0]["title"] == "New title"

    def test_deleting_a_reminder_invalidates_the_cache(self, car, client):
        reminder = self._create(car)
        client.force_authenticate(car.owner)
        client.get(reverse("reminder-list-create"))  # warm

        resp = client.delete(reverse("reminder-detail", args=[reminder.pk]))
        assert resp.status_code == 200  # SmartDetailView.delete_response() quirk, not 204 — see utils/Views.py

        listing = client.get(reverse("reminder-list-create"))
        results = listing.data.get("results", listing.data)
        assert results == []


@pytest.mark.django_db
class TestReminderComplete:
    """See #128 -- previously the only way to move a reminder's baseline
    forward was editing it by hand (or, for oil-change reminders only,
    logging a matching ServiceRecord)."""

    def test_resets_baseline_to_today_and_current_odometer(self, car, client):
        reminder = Reminder.objects.create(
            car=car, title="Brake pad replacement",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE_AND_MILEAGE,
            interval_km=20000, interval_months=12,
            baseline_odometer_km=10000, baseline_date=date(2025, 1, 1),
        )
        client.force_authenticate(car.owner)

        response = client.post(reverse("reminder-complete", args=[reminder.pk]))

        assert response.status_code == 200
        reminder.refresh_from_db()
        assert reminder.baseline_odometer_km == car.current_odometer_km
        assert reminder.baseline_date == timezone.localdate()
        assert reminder.next_due_odometer_km == car.current_odometer_km + 20000

    def test_date_only_reminder_leaves_odometer_baseline_untouched(self, car, client):
        reminder = Reminder.objects.create(
            car=car, title="Insurance renewal",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE,
            interval_months=12, baseline_date=date(2025, 1, 1),
        )
        client.force_authenticate(car.owner)

        client.post(reverse("reminder-complete", args=[reminder.pk]))

        reminder.refresh_from_db()
        assert reminder.baseline_odometer_km is None
        assert reminder.baseline_date == timezone.localdate()

    def test_response_reflects_the_now_ok_status(self, car, client):
        reminder = Reminder.objects.create(
            car=car, title="Brake pad replacement",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_MILEAGE,
            interval_km=1000, baseline_odometer_km=car.current_odometer_km - 999,
        )
        client.force_authenticate(car.owner)

        response = client.post(reverse("reminder-complete", args=[reminder.pk]))

        assert response.data["status"] == "ok"

    def test_rejects_a_reminder_the_owner_doesnt_own(self, car, client):
        other_owner = User.objects.create_user(email="other@example.com", password="str0ng-pass-123")
        other_car = Car.objects.create(owner=other_owner, make="Honda", model="Civic")
        reminder = Reminder.objects.create(
            car=other_car, title="Brake pad replacement",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE, interval_months=12,
            baseline_date=date(2025, 1, 1),
        )
        client.force_authenticate(car.owner)

        response = client.post(reverse("reminder-complete", args=[reminder.pk]))

        assert response.status_code == 404

    def test_requires_authentication(self, car):
        reminder = Reminder.objects.create(
            car=car, title="Brake pad replacement",
            tracking_method=Constants.REMINDER_TRACKING_METHOD_DATE, interval_months=12,
            baseline_date=date(2025, 1, 1),
        )
        api = APIClient()

        response = api.post(reverse("reminder-complete", args=[reminder.pk]))

        assert response.status_code == 401


class TestReminderCatalogCaching:

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    def test_catalog_is_only_computed_once(self, client):
        with patch("reminders.views.get_reminder_catalog", wraps=get_reminder_catalog) as mocked:
            first = client.get(reverse("reminder-catalog"))
            second = client.get(reverse("reminder-catalog"))

        assert mocked.call_count == 1
        assert first.data == second.data
