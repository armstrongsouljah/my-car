import pytest

from utils.Cloudinary import _public_id_from_url, delete_photos


class TestPublicIdFromUrl:

    def test_flat_public_id(self):
        url = "https://res.cloudinary.com/soultech/image/upload/v1699999999/abc123.jpg"
        assert _public_id_from_url(url) == "abc123"

    def test_public_id_with_folder(self):
        url = "https://res.cloudinary.com/soultech/image/upload/v1699999999/car_photos/user1/abc123.png"
        assert _public_id_from_url(url) == "car_photos/user1/abc123"

    def test_public_id_with_transformations(self):
        url = "https://res.cloudinary.com/soultech/image/upload/e_improve,w_900,h_700/v1699999999/abc123.jpg"
        assert _public_id_from_url(url) == "abc123"

    def test_non_cloudinary_url_returns_none(self):
        assert _public_id_from_url("https://example.com/photo.jpg") is None


@pytest.mark.django_db
class TestDeletePhotos:

    def test_skips_when_credentials_not_configured(self, settings, monkeypatch):
        settings.CLOUDINARY_CLOUD_NAME = ""
        settings.CLOUDINARY_API_KEY = ""
        settings.CLOUDINARY_API_SECRET = ""

        called = []
        monkeypatch.setattr("utils.Cloudinary.requests.post", lambda *a, **k: called.append(1))

        delete_photos(["https://res.cloudinary.com/soultech/image/upload/v1/abc.jpg"])

        assert called == []

    def test_skips_blank_urls(self, settings, monkeypatch):
        settings.CLOUDINARY_CLOUD_NAME = "soultech"
        settings.CLOUDINARY_API_KEY = "key"
        settings.CLOUDINARY_API_SECRET = "secret"

        called = []
        monkeypatch.setattr("utils.Cloudinary.requests.post", lambda *a, **k: called.append(1))

        delete_photos([None, ""])

        assert called == []

    def test_calls_destroy_for_each_configured_photo(self, settings, monkeypatch):
        settings.CLOUDINARY_CLOUD_NAME = "soultech"
        settings.CLOUDINARY_API_KEY = "key"
        settings.CLOUDINARY_API_SECRET = "secret"

        calls = []

        class FakeResponse:
            ok = True

        def fake_post(url, data, timeout):
            calls.append((url, data))
            return FakeResponse()

        monkeypatch.setattr("utils.Cloudinary.requests.post", fake_post)

        delete_photos(["https://res.cloudinary.com/soultech/image/upload/v1/car_photos/u1/abc.jpg"])

        assert len(calls) == 1
        url, data = calls[0]
        assert url == "https://api.cloudinary.com/v1_1/soultech/image/destroy"
        assert data["public_id"] == "car_photos/u1/abc"
        assert data["api_key"] == "key"
