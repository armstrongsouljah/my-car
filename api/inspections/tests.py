from datetime import date

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import Car
from inspections.models import Inspection


@pytest.fixture
def car(db):
    owner = User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")
    return Car.objects.create(owner=owner, make="Toyota", model="Corolla", current_odometer_km=40000)


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestInspectionListCaching:

    def test_car_scoped_list_is_cached_across_requests(self, car, client):
        client.force_authenticate(car.owner)
        first = client.get(reverse("inspection-list-create"), {"car": str(car.pk)})

        # Bypasses the API's own invalidation hook — proves the second
        # request is served from cache, not recomputed.
        Inspection.objects.create(car=car, inspection_date=date.today())

        second = client.get(reverse("inspection-list-create"), {"car": str(car.pk)})
        assert second.data == first.data

    def test_non_owner_cannot_read_another_owners_cached_list(self, car, client):
        client.force_authenticate(car.owner)
        client.get(reverse("inspection-list-create"), {"car": str(car.pk)})  # warm as owner

        other = User.objects.create_user(email="other@example.com", password="str0ng-pass-123")
        client.force_authenticate(other)
        resp = client.get(reverse("inspection-list-create"), {"car": str(car.pk)})
        results = resp.data.get("results", resp.data)
        assert results == []

    def test_creating_an_inspection_invalidates_the_cache(self, car, client):
        client.force_authenticate(car.owner)
        client.get(reverse("inspection-list-create"), {"car": str(car.pk)})  # warm

        resp = client.post(reverse("inspection-list-create"), {
            "car": str(car.pk), "inspection_date": date.today().isoformat(),
        }, format="json")
        assert resp.status_code == 201

        listing = client.get(reverse("inspection-list-create"), {"car": str(car.pk)})
        results = listing.data.get("results", listing.data)
        assert len(results) == 1

    def test_editing_an_inspection_invalidates_the_cache(self, car, client):
        inspection = Inspection.objects.create(car=car, inspection_date=date.today(), inspector_name="Alice")
        client.force_authenticate(car.owner)
        client.get(reverse("inspection-list-create"), {"car": str(car.pk)})  # warm

        resp = client.patch(
            reverse("inspection-detail", args=[inspection.pk]), {"inspector_name": "Bob"}, format="json"
        )
        assert resp.status_code == 200

        listing = client.get(reverse("inspection-list-create"), {"car": str(car.pk)})
        results = listing.data.get("results", listing.data)
        assert results[0]["inspector_name"] == "Bob"

    def test_deleting_an_inspection_invalidates_the_cache(self, car, client):
        inspection = Inspection.objects.create(car=car, inspection_date=date.today())
        client.force_authenticate(car.owner)
        client.get(reverse("inspection-list-create"), {"car": str(car.pk)})  # warm

        resp = client.delete(reverse("inspection-detail", args=[inspection.pk]))
        assert resp.status_code == 200  # SmartDetailView.delete_response() quirk, not 204 — see utils/Views.py

        listing = client.get(reverse("inspection-list-create"), {"car": str(car.pk)})
        results = listing.data.get("results", listing.data)
        assert results == []
