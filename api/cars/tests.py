from io import StringIO
from unittest.mock import Mock, patch

import pytest
import requests
from django.core.management import call_command
from django.test import override_settings
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


NEW_ACCOUNT_SETTINGS = {
    "NEW_CLOUD_NAME": "newcloud",
    "NEW_CLOUDINARY_API_KEY": "key123",
    "NEW_CLOUDINARY_API_SECRET": "secret123",
}
OLD_PHOTO_URL = "https://res.cloudinary.com/oldcloud/image/upload/v1700000000/car_photos/abc123.jpg"


def _ok_response(secure_url):
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"secure_url": secure_url}
    return response


@pytest.mark.django_db
class TestMigrateCloudinaryAssets:
    """See #48 — migrating car photos to a dedicated GlavBox Cloudinary
    account. A failed row must leave photo_url exactly as it was; nobody
    should lose a photo they already uploaded because of this command."""

    @override_settings(NEW_CLOUD_NAME="", NEW_CLOUDINARY_API_KEY="", NEW_CLOUDINARY_API_SECRET="")
    def test_without_credentials_errors_and_touches_nothing(self, car):
        # Explicitly blanked rather than relying on an unset ambient
        # environment -- a real local .env with real migration credentials
        # (exactly what this command needs to actually run) would otherwise
        # silently make this branch untestable.
        car.photo_url = OLD_PHOTO_URL
        car.save(update_fields=["photo_url"])
        stderr = StringIO()

        call_command("migrate_cloudinary_assets", stderr=stderr)

        assert "NEW_CLOUD_NAME" in stderr.getvalue()
        car.refresh_from_db()
        assert car.photo_url == OLD_PHOTO_URL

    @override_settings(**NEW_ACCOUNT_SETTINGS)
    def test_dry_run_does_not_call_the_network_or_touch_the_db(self, car):
        car.photo_url = OLD_PHOTO_URL
        car.save(update_fields=["photo_url"])
        stdout = StringIO()

        with patch("requests.post") as post:
            call_command("migrate_cloudinary_assets", stdout=stdout)

        post.assert_not_called()
        assert "would upload" in stdout.getvalue()
        assert "DRY RUN" in stdout.getvalue()
        car.refresh_from_db()
        assert car.photo_url == OLD_PHOTO_URL

    @override_settings(**NEW_ACCOUNT_SETTINGS)
    def test_execute_migrates_and_updates_photo_url(self, car):
        car.photo_url = OLD_PHOTO_URL
        car.save(update_fields=["photo_url"])
        new_url = "https://res.cloudinary.com/newcloud/image/upload/v1800000000/cars/abc123.jpg"

        with patch("requests.post", return_value=_ok_response(new_url)) as post:
            call_command("migrate_cloudinary_assets", "--execute")

        post.assert_called_once()
        # Keyed on the car's own id, not the old account's basename -- see
        # the collision-safety comment in the command itself.
        assert post.call_args.kwargs["data"]["public_id"] == f"cars/{car.id}"
        car.refresh_from_db()
        assert car.photo_url == new_url

    @override_settings(**NEW_ACCOUNT_SETTINGS)
    def test_a_failed_upload_leaves_the_row_untouched(self, car):
        car.photo_url = OLD_PHOTO_URL
        car.save(update_fields=["photo_url"])

        with patch("requests.post", side_effect=requests.RequestException("boom")):
            call_command("migrate_cloudinary_assets", "--execute", stderr=StringIO())

        car.refresh_from_db()
        assert car.photo_url == OLD_PHOTO_URL

    @override_settings(**NEW_ACCOUNT_SETTINGS)
    def test_a_malformed_response_leaves_the_row_untouched_and_does_not_crash_the_run(self, car):
        # A 200 with an unexpected body (missing secure_url) raises KeyError,
        # not requests.RequestException -- this must still be caught as a
        # per-row failure, not propagate and take down the whole command.
        car.photo_url = OLD_PHOTO_URL
        car.save(update_fields=["photo_url"])
        bad_response = Mock()
        bad_response.raise_for_status = Mock()
        bad_response.json.return_value = {}

        with patch("requests.post", return_value=bad_response):
            call_command("migrate_cloudinary_assets", "--execute", stderr=StringIO())

        car.refresh_from_db()
        assert car.photo_url == OLD_PHOTO_URL

    @override_settings(**NEW_ACCOUNT_SETTINGS)
    def test_already_migrated_cars_are_skipped(self, car):
        already = "https://res.cloudinary.com/newcloud/image/upload/v1800000000/cars/abc123.jpg"
        car.photo_url = already
        car.save(update_fields=["photo_url"])

        with patch("requests.post") as post:
            call_command("migrate_cloudinary_assets", "--execute")

        post.assert_not_called()
        car.refresh_from_db()
        assert car.photo_url == already

    @override_settings(**NEW_ACCOUNT_SETTINGS)
    def test_limit_caps_how_many_are_processed(self, owner):
        Car.objects.create(owner=owner, make="Toyota", model="Corolla", photo_url=OLD_PHOTO_URL)
        Car.objects.create(owner=owner, make="Honda", model="Civic", photo_url=OLD_PHOTO_URL)

        with patch("requests.post", return_value=_ok_response("https://res.cloudinary.com/newcloud/x.jpg")) as post:
            call_command("migrate_cloudinary_assets", "--execute", "--limit=1")

        post.assert_called_once()
