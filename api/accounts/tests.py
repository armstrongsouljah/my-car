import re
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User, EmailVerificationOTP
from utils import Constants


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def owner(db):
    user = User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    return user


@pytest.mark.django_db
class TestAuthFlow:

    def test_register_creates_unverified_user_and_otp(self, client):
        response = client.post(reverse("auth-register"), {
            "email": "new@example.com",
            "password": "str0ng-pass-123",
        })
        assert response.status_code == 201
        user = User.objects.get(email="new@example.com")
        assert user.is_email_verified is False
        assert EmailVerificationOTP.objects.filter(user=user, is_used=False).exists()

    def test_registration_email_carries_a_six_digit_code(self, client):
        from django.core import mail

        response = client.post(reverse("auth-register"), {
            "email": "sixdigit@example.com",
            "password": "str0ng-pass-123",
        })
        assert response.status_code == 201

        body = mail.outbox[-1].body
        codes = re.findall(r"\b\d{6}\b", body)
        assert codes, f"no 6-digit code in the email body: {body!r}"

        # The emailed code verifies, and it is not what sits in the database.
        stored = EmailVerificationOTP.objects.get(user__email="sixdigit@example.com")
        assert stored.otp != codes[0]
        assert stored.verify(codes[0]) is True

    def test_login_blocked_until_verified(self, client, db):
        User.objects.create_user(email="unverified@example.com", password="str0ng-pass-123")
        response = client.post(reverse("auth-login"), {
            "email": "unverified@example.com",
            "password": "str0ng-pass-123",
        })
        assert response.status_code == 403

    def test_verify_email_returns_tokens(self, client, db):
        user = User.objects.create_user(email="v@example.com", password="str0ng-pass-123")
        _, raw_otp = EmailVerificationOTP.create_for_user(user)
        response = client.post(reverse("auth-verify-email"), {"email": "v@example.com", "otp": raw_otp})
        assert response.status_code == 200
        assert "tokens" in response.data

    def test_login_returns_tokens(self, client, owner):
        response = client.post(reverse("auth-login"), {
            "email": "owner@example.com",
            "password": "str0ng-pass-123",
        })
        assert response.status_code == 200
        assert "access" in response.data["tokens"]

    def test_deactivate_account(self, client, owner):
        client.force_authenticate(owner)
        response = client.post(reverse("auth-deactivate"), {"password": "str0ng-pass-123"})
        assert response.status_code == 200
        owner.refresh_from_db()
        assert owner.is_active is False
        assert owner.deactivated_at is not None

    def test_deactivated_user_cannot_login(self, client, owner):
        owner.deactivate()
        response = client.post(reverse("auth-login"), {
            "email": "owner@example.com",
            "password": "str0ng-pass-123",
        })
        assert response.status_code in (401, 403)


@pytest.mark.django_db
class TestPurgeDeactivatedAccounts:

    def test_purges_accounts_past_the_grace_period(self, owner):
        from tasks import purge_deactivated_accounts_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS + 1)
        )

        purge_deactivated_accounts_task()

        assert not User.objects.filter(pk=owner.pk).exists()

    def test_purges_accounts_exactly_at_the_grace_period_boundary(self, owner):
        """deactivated_at__lte means the boundary day itself is purge-eligible."""
        from tasks import purge_deactivated_accounts_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS)
        )

        purge_deactivated_accounts_task()

        assert not User.objects.filter(pk=owner.pk).exists()

    def test_keeps_accounts_still_within_the_grace_period(self, owner):
        from tasks import purge_deactivated_accounts_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS - 1)
        )

        purge_deactivated_accounts_task()

        assert User.objects.filter(pk=owner.pk).exists()

    def test_keeps_active_accounts(self, owner):
        from tasks import purge_deactivated_accounts_task

        purge_deactivated_accounts_task()

        assert User.objects.filter(pk=owner.pk).exists()


@pytest.fixture
def throttled_rates(monkeypatch):
    """
    Turns throttling back on for a single test.

    The auth rates are disabled suite-wide in test_settings (counters live in
    the cache and would otherwise leak between tests). `THROTTLE_RATES` is read
    onto the class at import time, so overriding the setting at runtime has no
    effect — the class attribute is what has to be patched.
    """
    from django.core.cache import cache
    from rest_framework.throttling import SimpleRateThrottle

    def _apply(**rates):
        monkeypatch.setattr(
            SimpleRateThrottle, "THROTTLE_RATES", {**SimpleRateThrottle.THROTTLE_RATES, **rates}
        )
        cache.clear()

    yield _apply
    cache.clear()


@pytest.mark.django_db
class TestProfileEndpointScoping:
    """
    Regression: SmartDetailView.delete() ignored `deletable`, and ProfileView
    never scoped queryset(), so DELETE /auth/profile/ resolved to
    User.objects.filter() -> every user, and .first() (ordering -date_joined)
    deleted whoever signed up most recently.
    """

    def test_delete_on_profile_is_rejected(self, client, owner):
        victim = User.objects.create_user(email="victim@example.com", password="str0ng-pass-123")

        client.force_authenticate(owner)
        response = client.delete(reverse("auth-profile"))

        assert response.status_code == 403
        assert User.objects.filter(pk=victim.pk).exists()
        assert User.objects.filter(pk=owner.pk).exists()

    def test_patch_only_ever_touches_the_caller(self, client, owner):
        victim = User.objects.create_user(
            email="victim@example.com", password="str0ng-pass-123", first_name="Victim"
        )

        client.force_authenticate(owner)
        response = client.patch(reverse("auth-profile"), {"first_name": "Renamed"})

        assert response.status_code == 200
        victim.refresh_from_db()
        owner.refresh_from_db()
        assert victim.first_name == "Victim"
        assert owner.first_name == "Renamed"

    def test_get_returns_the_callers_own_profile(self, client, owner):
        User.objects.create_user(email="victim@example.com", password="str0ng-pass-123")

        client.force_authenticate(owner)
        response = client.get(reverse("auth-profile"))

        assert response.status_code == 200
        assert response.data["email"] == "owner@example.com"


@pytest.mark.django_db
class TestUnscopedDetailViewFailsLoudly:
    """The base queryset() must refuse to match the whole table."""

    def test_default_queryset_without_kwargs_raises(self):
        from django.core.exceptions import ImproperlyConfigured
        from utils.Views import SmartDetailView

        view = SmartDetailView()
        view.model = User

        with pytest.raises(ImproperlyConfigured):
            view.queryset()


@pytest.mark.django_db
class TestOTPBruteForce:

    def test_otp_is_burned_after_repeated_wrong_guesses(self, client):
        user = User.objects.create_user(email="brute@example.com", password="str0ng-pass-123")
        otp_instance, raw_otp = EmailVerificationOTP.create_for_user(user)
        wrong = "000000" if raw_otp != "000000" else "111111"

        for _ in range(Constants.OTP_MAX_FAILED_ATTEMPTS):
            response = client.post(reverse("auth-verify-email"), {"email": "brute@example.com", "otp": wrong})
            # Same generic rejection every time — see TestAccountEnumeration.
            assert response.status_code == 400

        otp_instance.refresh_from_db()
        assert otp_instance.is_used is True

        # Even the correct code is now dead — the owner must request a new one.
        response = client.post(reverse("auth-verify-email"), {"email": "brute@example.com", "otp": raw_otp})
        assert response.status_code == 400
        user.refresh_from_db()
        assert user.is_email_verified is False

    def test_correct_otp_still_verifies_within_the_attempt_budget(self, client):
        user = User.objects.create_user(email="ok@example.com", password="str0ng-pass-123")
        _, raw_otp = EmailVerificationOTP.create_for_user(user)
        wrong = "000000" if raw_otp != "000000" else "111111"

        client.post(reverse("auth-verify-email"), {"email": "ok@example.com", "otp": wrong})
        response = client.post(reverse("auth-verify-email"), {"email": "ok@example.com", "otp": raw_otp})

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_email_verified is True

    def test_a_fresh_otp_resets_the_attempt_budget(self, client):
        user = User.objects.create_user(email="reset@example.com", password="str0ng-pass-123")
        EmailVerificationOTP.create_for_user(user)
        for _ in range(Constants.OTP_MAX_FAILED_ATTEMPTS):
            client.post(reverse("auth-verify-email"), {"email": "reset@example.com", "otp": "000000"})

        _, raw_otp = EmailVerificationOTP.create_for_user(user)
        response = client.post(reverse("auth-verify-email"), {"email": "reset@example.com", "otp": raw_otp})

        assert response.status_code == 200


@pytest.mark.django_db
class TestAuthThrottling:

    def test_login_is_throttled(self, client, owner, throttled_rates):
        throttled_rates(auth_login="3/min")

        statuses = [
            client.post(reverse("auth-login"), {"email": "owner@example.com", "password": "wrong"}).status_code
            for _ in range(4)
        ]

        assert statuses[:3] == [401, 401, 401]
        assert statuses[3] == 429

    def test_otp_verification_is_throttled_per_email(self, client, throttled_rates):
        throttled_rates(auth_verify_otp="2/min")
        User.objects.create_user(email="a@example.com", password="str0ng-pass-123")
        User.objects.create_user(email="b@example.com", password="str0ng-pass-123")
        EmailVerificationOTP.create_for_user(User.objects.get(email="a@example.com"))
        EmailVerificationOTP.create_for_user(User.objects.get(email="b@example.com"))

        for _ in range(2):
            client.post(reverse("auth-verify-email"), {"email": "a@example.com", "otp": "000000"})
        blocked = client.post(reverse("auth-verify-email"), {"email": "a@example.com", "otp": "000000"})

        # A different target account is unaffected — the bucket is per email.
        other = client.post(reverse("auth-verify-email"), {"email": "b@example.com", "otp": "000000"})

        assert blocked.status_code == 429
        assert other.status_code == 400


class TestOTPGeneration:

    def test_otp_uses_the_csprng(self):
        import inspect

        from utils import Email as EmailUtil

        source = inspect.getsource(EmailUtil.generate_otp)
        assert "secrets." in source
        assert "random." not in source

    def test_otp_is_six_digits(self):
        from utils.Email import generate_otp

        otp = generate_otp()
        assert len(otp) == 6 and otp.isdigit()


@pytest.mark.django_db
class TestAccountEnumeration:
    """
    Registration, resend-OTP and verify-email must all look identical whether
    or not the address has an account behind it.
    """

    def test_register_looks_the_same_for_a_taken_address(self, client, owner):
        from django.core import mail

        fresh = client.post(reverse("auth-register"), {
            "email": "brand-new@example.com", "password": "str0ng-pass-123",
        })
        taken = client.post(reverse("auth-register"), {
            "email": "owner@example.com", "password": "str0ng-pass-123",
        })

        assert fresh.status_code == taken.status_code == 201
        # Only the caller-supplied address differs; the wording is identical.
        assert fresh.data["detail"].replace("brand-new@example.com", "") == \
            taken.data["detail"].replace("owner@example.com", "")

        # No second account, and no password overwrite on the existing one.
        assert User.objects.filter(email="owner@example.com").count() == 1
        owner.refresh_from_db()
        assert owner.check_password("str0ng-pass-123") is True

        # The address owner is told, since they're the only one who can act.
        assert mail.outbox[-1].to == ["owner@example.com"]
        assert "already have" in mail.outbox[-1].subject.lower()

    def test_resend_otp_looks_the_same_for_an_unknown_address(self, client):
        known = User.objects.create_user(email="unverified@example.com", password="str0ng-pass-123")

        hit = client.post(reverse("auth-resend-otp"), {"email": "unverified@example.com"})
        miss = client.post(reverse("auth-resend-otp"), {"email": "nobody@example.com"})

        assert hit.status_code == miss.status_code == 200
        assert hit.data["detail"].replace("unverified@example.com", "") == \
            miss.data["detail"].replace("nobody@example.com", "")

        # A code really was issued for the account that exists, and none for the
        # address that doesn't.
        assert EmailVerificationOTP.objects.filter(user=known, is_used=False).exists()
        assert not User.objects.filter(email="nobody@example.com").exists()

    def test_verify_email_looks_the_same_for_every_failure(self, client):
        user = User.objects.create_user(email="real@example.com", password="str0ng-pass-123")
        EmailVerificationOTP.create_for_user(user)

        unknown_account = client.post(
            reverse("auth-verify-email"), {"email": "nobody@example.com", "otp": "000000"})
        wrong_code = client.post(
            reverse("auth-verify-email"), {"email": "real@example.com", "otp": "000000"})
        already_verified = client.post(
            reverse("auth-verify-email"), {"email": "owner-verified@example.com", "otp": "000000"})

        bodies = {
            unknown_account.status_code: unknown_account.data,
            wrong_code.status_code: wrong_code.data,
            already_verified.status_code: already_verified.data,
        }
        assert list(bodies) == [400], "failure modes are distinguishable by status code"
        assert unknown_account.data == wrong_code.data == already_verified.data


@pytest.mark.django_db
class TestOTPStorage:

    def test_raw_code_is_never_stored(self):
        user = User.objects.create_user(email="hash@example.com", password="str0ng-pass-123")
        instance, raw_otp = EmailVerificationOTP.create_for_user(user)

        assert len(raw_otp) == 6 and raw_otp.isdigit()
        assert instance.otp != raw_otp
        assert raw_otp not in instance.otp
        assert instance.verify(raw_otp) is True
        assert instance.verify("000000" if raw_otp != "000000" else "111111") is False

    def test_otp_is_not_exposed_in_the_admin(self):
        from django.contrib import admin

        assert EmailVerificationOTP not in admin.site._registry
