from decimal import Decimal

import pytest

from utils.Cloudinary import _credentials_from_settings, _public_id_from_url, delete_photos
from utils.Currency import convert_amount, format_amount, load_latest_rates


class TestFormatAmount:

    def test_falls_back_to_a_bare_number_when_currency_is_unset(self):
        assert format_amount(1234.5, "") == "1,234.50"

    def test_falls_back_to_a_bare_number_for_an_unrecognized_currency(self):
        assert format_amount(1234.5, "ZZZ") == "1,234.50"

    def test_formats_with_the_currency_symbol(self):
        assert format_amount(1234.5, "USD") == "$ 1,234.50"

    def test_zero_decimal_currencies_drop_the_cents(self):
        assert format_amount(1234.7, "UGX") == "USh 1,235"


class TestConvertAmount:
    """See #40 — conversion always uses the latest fetched rate, never a
    rate keyed to the transaction's own date (a deliberate simplification)."""

    RATES = {"USD": Decimal("1"), "UGX": Decimal("1") / Decimal("3700"), "KES": Decimal("1") / Decimal("129")}

    def test_returns_amount_unchanged_when_currencies_match(self):
        assert convert_amount(100, "USD", "USD", self.RATES) == 100

    def test_returns_amount_unchanged_when_from_currency_is_unset(self):
        assert convert_amount(100, "", "USD", self.RATES) == 100

    def test_returns_amount_unchanged_when_to_currency_is_unset(self):
        assert convert_amount(100, "USD", "", self.RATES) == 100

    def test_returns_amount_unchanged_when_a_rate_is_missing(self):
        assert convert_amount(100, "USD", "EUR", self.RATES) == 100

    def test_converts_through_usd_as_the_pivot(self):
        converted = convert_amount(Decimal("3700"), "UGX", "USD", self.RATES)
        assert round(converted, 2) == Decimal("1.00")

    def test_converts_between_two_non_usd_currencies(self):
        converted = convert_amount(Decimal("3700"), "UGX", "KES", self.RATES)
        assert round(converted, 2) == Decimal("129.00")


@pytest.mark.django_db
class TestLoadLatestRates:

    def test_picks_the_most_recent_rate_per_currency(self):
        from datetime import date

        from expenses.models import ExchangeRate

        ExchangeRate.objects.create(date=date(2026, 1, 1), currency="USD", rate_to_usd=Decimal("1"))
        ExchangeRate.objects.create(date=date(2026, 1, 2), currency="USD", rate_to_usd=Decimal("1"))
        ExchangeRate.objects.create(date=date(2026, 1, 1), currency="UGX", rate_to_usd=Decimal("0.00027"))
        ExchangeRate.objects.create(date=date(2026, 1, 3), currency="UGX", rate_to_usd=Decimal("0.00030"))

        rates = load_latest_rates()

        assert rates["UGX"] == Decimal("0.00030")
        assert rates["USD"] == Decimal("1")


class TestCredentialsFromSettings:

    def test_parses_the_standard_cloudinary_url_form(self, settings):
        settings.CLOUDINARY_URL = "cloudinary://mykey:mysecret@soultech"
        assert _credentials_from_settings() == ("soultech", "mykey", "mysecret")

    def test_returns_none_when_unset(self, settings):
        settings.CLOUDINARY_URL = ""
        assert _credentials_from_settings() is None

    def test_returns_none_for_a_malformed_url(self, settings):
        settings.CLOUDINARY_URL = "not-a-cloudinary-url"
        assert _credentials_from_settings() is None


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
        settings.CLOUDINARY_URL = ""

        called = []
        monkeypatch.setattr("utils.Cloudinary.requests.post", lambda *a, **k: called.append(1))

        delete_photos(["https://res.cloudinary.com/soultech/image/upload/v1/abc.jpg"])

        assert called == []

    def test_skips_blank_urls(self, settings, monkeypatch):
        settings.CLOUDINARY_URL = "cloudinary://key:secret@soultech"

        called = []
        monkeypatch.setattr("utils.Cloudinary.requests.post", lambda *a, **k: called.append(1))

        delete_photos([None, ""])

        assert called == []

    def test_calls_destroy_for_each_configured_photo(self, settings, monkeypatch):
        settings.CLOUDINARY_URL = "cloudinary://key:secret@soultech"

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
        assert data["invalidate"] == "true"

    def test_logs_but_does_not_raise_on_a_failed_destroy(self, settings, monkeypatch):
        settings.CLOUDINARY_URL = "cloudinary://key:secret@soultech"

        class FakeResponse:
            ok = False
            status_code = 500
            text = "internal error"

        monkeypatch.setattr("utils.Cloudinary.requests.post", lambda *a, **k: FakeResponse())

        # Best-effort by design: a Cloudinary-side failure shouldn't raise and
        # block the account deletion this cleanup is part of.
        delete_photos(["https://res.cloudinary.com/soultech/image/upload/v1/abc.jpg"])

    def test_logs_but_does_not_raise_on_a_request_error(self, settings, monkeypatch):
        import requests

        settings.CLOUDINARY_URL = "cloudinary://key:secret@soultech"

        def raise_error(*args, **kwargs):
            raise requests.ConnectionError("boom")

        monkeypatch.setattr("utils.Cloudinary.requests.post", raise_error)

        delete_photos(["https://res.cloudinary.com/soultech/image/upload/v1/abc.jpg"])
