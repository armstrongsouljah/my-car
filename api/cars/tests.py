import pytest
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import Car


@pytest.fixture
def owner(db):
    user = User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    return user


@pytest.fixture
def car(owner):
    return Car.objects.create(owner=owner, make="Toyota", model="Corolla", current_odometer_km=50_000)


@pytest.mark.django_db
class TestRecordOdometer:
    """See #55 — the mileage quick-update page needs an explicit override for
    the rare legitimate backwards reading (engine/odometer replacement)."""

    def test_moves_the_reading_forward(self, car):
        car.record_odometer(51_000)
        car.refresh_from_db()
        assert car.current_odometer_km == 51_000
        assert car.odometer_updated_at is not None

    def test_a_lower_reading_is_a_no_op_by_default(self, car):
        car.record_odometer(40_000)
        car.refresh_from_db()
        assert car.current_odometer_km == 50_000

    def test_allow_decrease_lets_a_lower_reading_through(self, car):
        car.record_odometer(40_000, allow_decrease=True)
        car.refresh_from_db()
        assert car.current_odometer_km == 40_000


@pytest.mark.django_db
class TestCarDetailPatchOdometer:
    def test_forward_reading_is_accepted(self, owner, car):
        client = APIClient()
        client.force_authenticate(owner)

        response = client.patch(f"/api/v1/cars/{car.pk}/", {"current_odometer_km": 55_000}, format="json")

        assert response.status_code == 200
        car.refresh_from_db()
        assert car.current_odometer_km == 55_000

    def test_backwards_reading_is_rejected_without_override(self, owner, car):
        client = APIClient()
        client.force_authenticate(owner)

        response = client.patch(f"/api/v1/cars/{car.pk}/", {"current_odometer_km": 30_000}, format="json")

        assert response.status_code == 400
        car.refresh_from_db()
        assert car.current_odometer_km == 50_000

    def test_backwards_reading_is_accepted_with_override(self, owner, car):
        client = APIClient()
        client.force_authenticate(owner)

        response = client.patch(
            f"/api/v1/cars/{car.pk}/",
            {"current_odometer_km": 30_000, "allow_odometer_decrease": True},
            format="json",
        )

        assert response.status_code == 200
        car.refresh_from_db()
        assert car.current_odometer_km == 30_000

    def test_allow_odometer_decrease_is_never_persisted(self, owner, car):
        client = APIClient()
        client.force_authenticate(owner)

        response = client.patch(
            f"/api/v1/cars/{car.pk}/",
            {"current_odometer_km": 30_000, "allow_odometer_decrease": True},
            format="json",
        )

        assert "allow_odometer_decrease" not in response.data
