import re
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User, EmailVerificationOTP, PasswordResetOTP
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

    def test_deactivate_sends_confirmation_email(self, client, owner):
        from django.core import mail

        client.force_authenticate(owner)
        response = client.post(reverse("auth-deactivate"), {"password": "str0ng-pass-123"})

        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [owner.email]
        assert str(Constants.ACCOUNT_DELETION_GRACE_DAYS) in mail.outbox[0].body

    def test_deactivate_resets_a_previously_sent_deletion_reminder(self, owner):
        """
        A user reactivated by support, then deactivated again, is on a fresh
        30-day lifecycle — the old reminder timestamp shouldn't survive and
        suppress this lifecycle's own 15-day reminder.
        """
        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(deletion_reminder_sent_at=timezone.now())

        User.objects.filter(pk=owner.pk).update(is_active=True, deactivated_at=None)  # support reactivates
        owner.refresh_from_db()

        owner.deactivate()

        assert owner.deletion_reminder_sent_at is None


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

    def test_keeps_never_verified_accounts_even_if_flagged_inactive(self, owner):
        """
        deactivate() is only ever reachable by an authenticated (and so
        already-verified) user, but this guards the purge query directly
        against the lifecycle's own definition rather than relying on that
        being true forever — e.g. a future admin action or #23's unverified-
        signup sweep setting is_active/deactivated_at without also touching
        is_email_verified shouldn't make this task eligible for it.
        """
        from tasks import purge_deactivated_accounts_task

        User.objects.filter(pk=owner.pk).update(
            is_active=False,
            is_email_verified=False,
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS),
        )

        purge_deactivated_accounts_task()

        assert User.objects.filter(pk=owner.pk).exists()

    def test_sends_final_email_before_deleting(self, owner):
        from django.core import mail

        from tasks import purge_deactivated_accounts_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS)
        )

        purge_deactivated_accounts_task()

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [owner.email]

    def test_cleans_up_cloudinary_photos(self, owner, monkeypatch):
        from cars.models import Car
        from tasks import purge_deactivated_accounts_task

        photo_url = "https://res.cloudinary.com/soultech/image/upload/v1/car_photos/u1/abc.jpg"
        Car.objects.create(owner=owner, make="Toyota", model="Corolla", photo_url=photo_url)
        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS)
        )

        cleaned_up = []
        monkeypatch.setattr("utils.Cloudinary.delete_photos", lambda urls: cleaned_up.extend(urls))

        purge_deactivated_accounts_task()

        assert cleaned_up == [photo_url]

    def test_skips_cloudinary_cleanup_for_cars_without_photos(self, owner, monkeypatch):
        from cars.models import Car
        from tasks import purge_deactivated_accounts_task

        Car.objects.create(owner=owner, make="Toyota", model="Corolla")
        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS)
        )

        cleaned_up = []
        monkeypatch.setattr("utils.Cloudinary.delete_photos", lambda urls: cleaned_up.extend(urls))

        purge_deactivated_accounts_task()

        assert cleaned_up == []


@pytest.mark.django_db
class TestAccountDeletionReminder:

    def test_sends_reminder_at_the_configured_day(self, owner):
        from django.core import mail

        from tasks import send_account_deletion_reminder_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_REMINDER_DAYS)
        )

        send_account_deletion_reminder_task()

        owner.refresh_from_db()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [owner.email]
        assert owner.deletion_reminder_sent_at is not None

    def test_does_not_send_before_the_configured_day(self, owner):
        from django.core import mail

        from tasks import send_account_deletion_reminder_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_REMINDER_DAYS - 1)
        )

        send_account_deletion_reminder_task()

        owner.refresh_from_db()
        assert len(mail.outbox) == 0
        assert owner.deletion_reminder_sent_at is None

    def test_does_not_resend(self, owner):
        from django.core import mail

        from tasks import send_account_deletion_reminder_task

        owner.deactivate()
        already_sent = timezone.now() - timedelta(days=1)
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_REMINDER_DAYS + 5),
            deletion_reminder_sent_at=already_sent,
        )

        send_account_deletion_reminder_task()

        assert len(mail.outbox) == 0

    def test_does_not_send_once_past_the_purge_cutoff(self, owner):
        """
        Guards against send_account_deletion_reminder_task and
        purge_deactivated_accounts_task running out of order on the same day
        (or a prior run of this task never having claimed the row): an
        account already eligible for purge shouldn't get a misleading
        "N days left" email right as, or after, it's deleted.
        """
        from django.core import mail

        from tasks import send_account_deletion_reminder_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS)
        )

        send_account_deletion_reminder_task()

        owner.refresh_from_db()
        assert len(mail.outbox) == 0
        assert owner.deletion_reminder_sent_at is None

    def test_skips_active_accounts(self, owner):
        from django.core import mail

        from tasks import send_account_deletion_reminder_task

        send_account_deletion_reminder_task()

        assert len(mail.outbox) == 0

    def test_skips_never_verified_accounts(self, owner):
        from django.core import mail

        from tasks import send_account_deletion_reminder_task

        User.objects.filter(pk=owner.pk).update(
            is_active=False,
            is_email_verified=False,
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_REMINDER_DAYS),
        )

        send_account_deletion_reminder_task()

        assert len(mail.outbox) == 0

    def test_claims_but_does_not_confirm_when_the_send_fails(self, owner, monkeypatch):
        from django.core import mail

        from tasks import send_account_deletion_reminder_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_REMINDER_DAYS)
        )
        monkeypatch.setattr(
            "utils.Email.send_deletion_reminder_email",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("smtp down")),
        )

        send_account_deletion_reminder_task()

        owner.refresh_from_db()
        assert len(mail.outbox) == 0
        assert owner.deletion_reminder_sent_at is None
        assert owner.deletion_reminder_queued_at is not None

    def test_does_not_redispatch_while_the_claim_lease_is_still_fresh(self, owner, monkeypatch):
        """A second sweep run shortly after a failed send shouldn't pile on another attempt."""
        from tasks import send_account_deletion_reminder_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_REMINDER_DAYS)
        )
        calls = []

        def failing_send(**kwargs):
            calls.append(1)
            raise RuntimeError("smtp down")

        monkeypatch.setattr("utils.Email.send_deletion_reminder_email", failing_send)
        send_account_deletion_reminder_task()

        send_account_deletion_reminder_task()

        assert len(calls) == 1

    def test_retries_once_the_claim_lease_goes_stale(self, owner):
        from django.core import mail

        from tasks import send_account_deletion_reminder_task

        owner.deactivate()
        User.objects.filter(pk=owner.pk).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_REMINDER_DAYS),
            deletion_reminder_queued_at=timezone.now() - timedelta(hours=Constants.REMINDER_CLAIM_LEASE_HOURS + 1),
        )

        send_account_deletion_reminder_task()

        owner.refresh_from_db()
        assert len(mail.outbox) == 1
        assert owner.deletion_reminder_sent_at is not None

    def test_one_failing_send_does_not_block_another_users_reminder(self, owner, monkeypatch):
        from django.core import mail

        from tasks import send_account_deletion_reminder_task
        from utils import Email

        failing = User.objects.create_user(email="failing@example.com", password="str0ng-pass-123")
        failing.is_email_verified = True
        failing.save(update_fields=["is_email_verified"])
        failing.deactivate()
        owner.deactivate()
        User.objects.filter(pk__in=[owner.pk, failing.pk]).update(
            deactivated_at=timezone.now() - timedelta(days=Constants.ACCOUNT_DELETION_REMINDER_DAYS)
        )

        real_send = Email.send_deletion_reminder_email

        def flaky_send(email, **kwargs):
            if email == "failing@example.com":
                raise RuntimeError("smtp down")
            return real_send(email=email, **kwargs)

        monkeypatch.setattr("utils.Email.send_deletion_reminder_email", flaky_send)

        send_account_deletion_reminder_task()

        owner.refresh_from_db()
        failing.refresh_from_db()
        assert owner.deletion_reminder_sent_at is not None
        assert failing.deletion_reminder_sent_at is None
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [owner.email]


@pytest.fixture
def unverified_signup(db):
    return User.objects.create_user(email="unverified@example.com", password="str0ng-pass-123")


@pytest.mark.django_db
class TestEmailVerificationReminder:

    def test_sends_reminder_at_the_configured_day_with_a_fresh_otp(self, unverified_signup):
        from django.core import mail

        from accounts.models import EmailVerificationOTP
        from tasks import send_email_verification_reminder_task

        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_REMINDER_DAYS)
        )

        send_email_verification_reminder_task()

        unverified_signup.refresh_from_db()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [unverified_signup.email]
        assert unverified_signup.verify_reminder_sent_at is not None
        assert EmailVerificationOTP.objects.filter(user=unverified_signup, is_used=False).exists()

    def test_does_not_send_before_the_configured_day(self, unverified_signup):
        from django.core import mail

        from tasks import send_email_verification_reminder_task

        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_REMINDER_DAYS - 1)
        )

        send_email_verification_reminder_task()

        unverified_signup.refresh_from_db()
        assert len(mail.outbox) == 0
        assert unverified_signup.verify_reminder_sent_at is None

    def test_does_not_resend(self, unverified_signup):
        from django.core import mail

        from tasks import send_email_verification_reminder_task

        already_sent = timezone.now() - timedelta(days=1)
        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_REMINDER_DAYS + 5),
            verify_reminder_sent_at=already_sent,
        )

        send_email_verification_reminder_task()

        assert len(mail.outbox) == 0

    def test_does_not_send_once_past_the_purge_cutoff(self, unverified_signup):
        """
        Guards against send_email_verification_reminder_task and
        purge_unverified_accounts_task running out of order on the same day:
        an account already eligible for purge shouldn't get a misleading
        "N days left" email right as, or after, it's deleted.
        """
        from django.core import mail

        from tasks import send_email_verification_reminder_task

        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_PURGE_DAYS)
        )

        send_email_verification_reminder_task()

        unverified_signup.refresh_from_db()
        assert len(mail.outbox) == 0
        assert unverified_signup.verify_reminder_sent_at is None

    def test_skips_verified_accounts(self, owner):
        from django.core import mail

        from tasks import send_email_verification_reminder_task

        User.objects.filter(pk=owner.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_REMINDER_DAYS)
        )

        send_email_verification_reminder_task()

        assert len(mail.outbox) == 0

    def test_claims_but_does_not_confirm_when_the_send_fails(self, unverified_signup, monkeypatch):
        from django.core import mail

        from tasks import send_email_verification_reminder_task

        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_REMINDER_DAYS)
        )
        monkeypatch.setattr(
            "utils.Email.send_verify_email_reminder_email",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("smtp down")),
        )

        send_email_verification_reminder_task()

        unverified_signup.refresh_from_db()
        assert len(mail.outbox) == 0
        assert unverified_signup.verify_reminder_sent_at is None
        assert unverified_signup.verify_reminder_queued_at is not None

    def test_does_not_redispatch_while_the_claim_lease_is_still_fresh(self, unverified_signup, monkeypatch):
        """A second sweep run shortly after a failed send shouldn't pile on another attempt."""
        from tasks import send_email_verification_reminder_task

        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_REMINDER_DAYS)
        )
        calls = []

        def failing_send(**kwargs):
            calls.append(1)
            raise RuntimeError("smtp down")

        monkeypatch.setattr("utils.Email.send_verify_email_reminder_email", failing_send)
        send_email_verification_reminder_task()

        send_email_verification_reminder_task()

        assert len(calls) == 1

    def test_retries_once_the_claim_lease_goes_stale(self, unverified_signup):
        from django.core import mail

        from tasks import send_email_verification_reminder_task

        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_REMINDER_DAYS),
            verify_reminder_queued_at=timezone.now() - timedelta(hours=Constants.REMINDER_CLAIM_LEASE_HOURS + 1),
        )

        send_email_verification_reminder_task()

        unverified_signup.refresh_from_db()
        assert len(mail.outbox) == 1
        assert unverified_signup.verify_reminder_sent_at is not None

    def test_one_failing_send_does_not_block_another_users_reminder(self, unverified_signup, monkeypatch):
        from django.core import mail

        from tasks import send_email_verification_reminder_task
        from utils import Email

        failing = User.objects.create_user(email="failing@example.com", password="str0ng-pass-123")
        User.objects.filter(pk__in=[unverified_signup.pk, failing.pk]).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_REMINDER_DAYS)
        )

        real_send = Email.send_verify_email_reminder_email

        def flaky_send(email, **kwargs):
            if email == "failing@example.com":
                raise RuntimeError("smtp down")
            return real_send(email=email, **kwargs)

        monkeypatch.setattr("utils.Email.send_verify_email_reminder_email", flaky_send)

        send_email_verification_reminder_task()

        unverified_signup.refresh_from_db()
        failing.refresh_from_db()
        assert unverified_signup.verify_reminder_sent_at is not None
        assert failing.verify_reminder_sent_at is None
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [unverified_signup.email]


@pytest.mark.django_db
class TestPurgeUnverifiedAccounts:

    def test_purges_accounts_past_the_purge_cutoff(self, unverified_signup):
        from tasks import purge_unverified_accounts_task

        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_PURGE_DAYS + 1)
        )

        purge_unverified_accounts_task()

        assert not User.objects.filter(pk=unverified_signup.pk).exists()

    def test_purges_accounts_exactly_at_the_purge_cutoff_boundary(self, unverified_signup):
        """date_joined__lte means the boundary day itself is purge-eligible."""
        from tasks import purge_unverified_accounts_task

        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_PURGE_DAYS)
        )

        purge_unverified_accounts_task()

        assert not User.objects.filter(pk=unverified_signup.pk).exists()

    def test_keeps_accounts_still_within_the_grace_period(self, unverified_signup):
        from tasks import purge_unverified_accounts_task

        User.objects.filter(pk=unverified_signup.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_PURGE_DAYS - 1)
        )

        purge_unverified_accounts_task()

        assert User.objects.filter(pk=unverified_signup.pk).exists()

    def test_keeps_verified_accounts(self, owner):
        from tasks import purge_unverified_accounts_task

        User.objects.filter(pk=owner.pk).update(
            date_joined=timezone.now() - timedelta(days=Constants.EMAIL_VERIFY_PURGE_DAYS)
        )

        purge_unverified_accounts_task()

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
class TestMileageReminders:

    @pytest.fixture
    def due_owner(self, owner):
        from cars.models import Car

        owner.mileage_reminder_frequency = Constants.MILEAGE_REMINDER_DAILY
        owner.save(update_fields=["mileage_reminder_frequency"])
        Car.objects.create(owner=owner, make="Toyota", model="Corolla")
        return owner

    def test_sends_reminder_for_a_due_car(self, due_owner):
        from django.core import mail

        from tasks import send_mileage_reminders_task

        send_mileage_reminders_task()

        due_owner.refresh_from_db()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [due_owner.email]
        assert due_owner.last_mileage_reminder_at is not None

    def test_skips_a_user_reminded_within_the_cadence_window(self, due_owner):
        from django.core import mail

        from tasks import send_mileage_reminders_task

        User.objects.filter(pk=due_owner.pk).update(last_mileage_reminder_at=timezone.now())

        send_mileage_reminders_task()

        assert len(mail.outbox) == 0

    def test_skips_off_and_inactive_users(self, owner):
        from django.core import mail

        from cars.models import Car
        from tasks import send_mileage_reminders_task

        Car.objects.create(owner=owner, make="Toyota", model="Corolla")  # frequency defaults to "off"

        send_mileage_reminders_task()

        assert len(mail.outbox) == 0

    def test_skips_a_user_with_no_active_cars(self, owner):
        from django.core import mail

        from tasks import send_mileage_reminders_task

        owner.mileage_reminder_frequency = Constants.MILEAGE_REMINDER_DAILY
        owner.save(update_fields=["mileage_reminder_frequency"])

        send_mileage_reminders_task()

        assert len(mail.outbox) == 0

    def test_claims_but_does_not_confirm_when_the_send_fails(self, due_owner, monkeypatch):
        from django.core import mail

        from tasks import send_mileage_reminders_task

        monkeypatch.setattr(
            "utils.Email.send_mileage_reminder_email",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("smtp down")),
        )

        send_mileage_reminders_task()

        due_owner.refresh_from_db()
        assert len(mail.outbox) == 0
        assert due_owner.last_mileage_reminder_at is None
        assert due_owner.mileage_reminder_queued_at is not None

    def test_does_not_redispatch_while_the_claim_lease_is_still_fresh(self, due_owner, monkeypatch):
        from tasks import send_mileage_reminders_task

        calls = []

        def failing_send(**kwargs):
            calls.append(1)
            raise RuntimeError("smtp down")

        monkeypatch.setattr("utils.Email.send_mileage_reminder_email", failing_send)
        send_mileage_reminders_task()

        send_mileage_reminders_task()

        assert len(calls) == 1

    def test_retries_once_the_claim_lease_goes_stale(self, due_owner):
        from django.core import mail

        from tasks import send_mileage_reminders_task

        User.objects.filter(pk=due_owner.pk).update(
            mileage_reminder_queued_at=timezone.now() - timedelta(hours=Constants.REMINDER_CLAIM_LEASE_HOURS + 1),
        )

        send_mileage_reminders_task()

        due_owner.refresh_from_db()
        assert len(mail.outbox) == 1
        assert due_owner.last_mileage_reminder_at is not None

    def test_send_task_does_not_redeliver_once_already_confirmed(self, due_owner):
        """
        Guards against Celery's at-least-once delivery: a redelivered message
        (or a stale-lease reclaim racing a slow-but-eventually-successful
        send) for a user already confirmed sent this cycle must not
        double-send.
        """
        from django.core import mail

        from tasks import send_mileage_reminder_email_task

        User.objects.filter(pk=due_owner.pk).update(last_mileage_reminder_at=timezone.now())

        send_mileage_reminder_email_task(user_id=due_owner.pk, cars=[])

        assert len(mail.outbox) == 0

    def test_send_task_skips_a_user_who_turned_reminders_off_after_being_claimed(self, due_owner):
        from django.core import mail

        from tasks import send_mileage_reminder_email_task

        User.objects.filter(pk=due_owner.pk).update(mileage_reminder_frequency=Constants.MILEAGE_REMINDER_OFF)

        send_mileage_reminder_email_task(user_id=due_owner.pk, cars=[])

        assert len(mail.outbox) == 0

    def test_send_task_clears_the_lease_on_success(self, due_owner):
        from tasks import send_mileage_reminder_email_task

        User.objects.filter(pk=due_owner.pk).update(mileage_reminder_queued_at=timezone.now())

        send_mileage_reminder_email_task(user_id=due_owner.pk, cars=[])

        due_owner.refresh_from_db()
        assert due_owner.mileage_reminder_queued_at is None


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

    def test_failed_attempt_counter_does_not_lose_a_racing_update(self):
        """
        Two verify requests can each load the same OTP row before either
        writes back. A naive `self.failed_attempts += 1; self.save()` would
        have both start from the same stale count and one increment would be
        lost — this pins the atomic F() update instead.
        """
        user = User.objects.create_user(email="racer3@example.com", password="str0ng-pass-123")
        otp, _ = EmailVerificationOTP.create_for_user(user)

        stale_a = EmailVerificationOTP.objects.get(pk=otp.pk)
        stale_b = EmailVerificationOTP.objects.get(pk=otp.pk)

        stale_a.register_failed_attempt()
        stale_b.register_failed_attempt()

        otp.refresh_from_db()
        assert otp.failed_attempts == 2


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

    def test_register_reissues_a_code_for_an_unverified_retry(self, client):
        from django.core import mail

        unverified = User.objects.create_user(email="unverified@example.com", password="first-pass-123")
        first_otp, _ = EmailVerificationOTP.create_for_user(unverified)

        retry = client.post(reverse("auth-register"), {
            "email": "unverified@example.com", "password": "second-pass-456",
        })

        assert retry.status_code == 201
        # No second account, and the original password is untouched.
        assert User.objects.filter(email="unverified@example.com").count() == 1
        unverified.refresh_from_db()
        assert unverified.check_password("first-pass-123") is True

        # A fresh code went out — not the "you already have an account" email,
        # since that would just send them to a login that rejects them for
        # being unverified.
        assert mail.outbox[-1].to == ["unverified@example.com"]
        assert "already have" not in mail.outbox[-1].subject.lower()

        first_otp.refresh_from_db()
        assert first_otp.is_used is True
        assert EmailVerificationOTP.objects.filter(user=unverified, is_used=False).count() == 1

    def test_register_survives_a_race_on_email_uniqueness(self, client, monkeypatch):
        """
        The pre-save UniqueValidator was removed from RegisterSerializer since
        it was itself an enumeration oracle, so the DB's unique constraint is
        now the only thing standing between two concurrent registrations for
        the same brand-new address (e.g. a double-clicked submit button).

        Simulates the race by making the existence check miss a row that's
        already there — the same outcome as another request's insert landing
        in the gap between our check and our own save() — and lets the real
        DB raise the real IntegrityError rather than faking one.
        """
        winner = User.objects.create_user(email="racer@example.com", password="whoever-won-123")

        real_filter = User.objects.filter
        calls = {"n": 0}

        def miss_the_row_once(*args, **kwargs):
            calls["n"] += 1
            return User.objects.none() if calls["n"] == 1 else real_filter(*args, **kwargs)

        monkeypatch.setattr(User.objects, "filter", miss_the_row_once)

        response = client.post(reverse("auth-register"), {
            "email": "racer@example.com", "password": "str0ng-pass-123",
        })

        assert response.status_code == 201
        assert User.objects.filter(email="racer@example.com").count() == 1
        # The account that actually won the race is untouched.
        winner.refresh_from_db()
        assert winner.check_password("whoever-won-123") is True

    def test_register_reraises_an_integrity_error_unrelated_to_email(self, client, monkeypatch):
        """
        An IntegrityError from some other unique constraint has no "winner"
        row at this email to fall back to — that must surface as a real
        error, not get silently swallowed into a fake 201.
        """
        from django.db import IntegrityError

        from accounts.serializers import RegisterSerializer

        def unrelated_integrity_error(self, *args, **kwargs):
            raise IntegrityError("unique constraint on some other field")

        monkeypatch.setattr(RegisterSerializer, "save", unrelated_integrity_error)

        with pytest.raises(IntegrityError):
            client.post(reverse("auth-register"), {
                "email": "nobody-yet@example.com", "password": "str0ng-pass-123",
            })

        assert not User.objects.filter(email="nobody-yet@example.com").exists()

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
class TestPasswordReset:

    def test_request_reset_issues_an_otp_for_a_known_account(self, client, owner):
        response = client.post(reverse("auth-password-reset-request"), {"email": "owner@example.com"})
        assert response.status_code == 200
        assert PasswordResetOTP.objects.filter(user=owner, is_used=False).exists()

    def test_request_reset_looks_the_same_for_an_unknown_address(self, client, owner):
        hit = client.post(reverse("auth-password-reset-request"), {"email": "owner@example.com"})
        miss = client.post(reverse("auth-password-reset-request"), {"email": "nobody@example.com"})

        assert hit.status_code == miss.status_code == 200
        assert hit.data["detail"].replace("owner@example.com", "") == \
            miss.data["detail"].replace("nobody@example.com", "")

    def test_request_reset_does_not_issue_a_code_for_a_deactivated_account(self, client, owner):
        owner.deactivate()
        client.post(reverse("auth-password-reset-request"), {"email": "owner@example.com"})
        assert not PasswordResetOTP.objects.filter(user=owner, is_used=False).exists()

    def test_confirm_reset_sets_new_password_and_returns_tokens(self, client, owner):
        _, raw_otp = PasswordResetOTP.create_for_user(owner)
        response = client.post(reverse("auth-password-reset-confirm"), {
            "email": "owner@example.com",
            "otp": raw_otp,
            "new_password": "brand-new-pass-123",
            "confirm_new_password": "brand-new-pass-123",
        })

        assert response.status_code == 200
        assert "tokens" in response.data
        owner.refresh_from_db()
        assert owner.check_password("brand-new-pass-123") is True
        assert owner.check_password("str0ng-pass-123") is False

    def test_confirm_reset_rejects_mismatched_passwords(self, client, owner):
        _, raw_otp = PasswordResetOTP.create_for_user(owner)
        response = client.post(reverse("auth-password-reset-confirm"), {
            "email": "owner@example.com",
            "otp": raw_otp,
            "new_password": "brand-new-pass-123",
            "confirm_new_password": "does-not-match-456",
        })

        assert response.status_code == 400
        owner.refresh_from_db()
        assert owner.check_password("str0ng-pass-123") is True

    def test_confirm_reset_rejects_wrong_code(self, client, owner):
        _, raw_otp = PasswordResetOTP.create_for_user(owner)
        wrong = "000000" if raw_otp != "000000" else "111111"
        response = client.post(reverse("auth-password-reset-confirm"), {
            "email": "owner@example.com",
            "otp": wrong,
            "new_password": "brand-new-pass-123",
            "confirm_new_password": "brand-new-pass-123",
        })

        assert response.status_code == 400
        owner.refresh_from_db()
        assert owner.check_password("str0ng-pass-123") is True

    def test_confirm_reset_looks_the_same_for_every_failure(self, client, owner):
        PasswordResetOTP.create_for_user(owner)

        unknown_account = client.post(reverse("auth-password-reset-confirm"), {
            "email": "nobody@example.com", "otp": "000000",
            "new_password": "brand-new-pass-123", "confirm_new_password": "brand-new-pass-123",
        })
        wrong_code = client.post(reverse("auth-password-reset-confirm"), {
            "email": "owner@example.com", "otp": "000000",
            "new_password": "brand-new-pass-123", "confirm_new_password": "brand-new-pass-123",
        })

        assert unknown_account.status_code == wrong_code.status_code == 400
        assert unknown_account.data == wrong_code.data

    def test_otp_is_burned_after_repeated_wrong_guesses(self, client, owner):
        otp_instance, raw_otp = PasswordResetOTP.create_for_user(owner)
        wrong = "000000" if raw_otp != "000000" else "111111"

        for _ in range(Constants.OTP_MAX_FAILED_ATTEMPTS):
            client.post(reverse("auth-password-reset-confirm"), {
                "email": "owner@example.com", "otp": wrong,
                "new_password": "brand-new-pass-123", "confirm_new_password": "brand-new-pass-123",
            })

        otp_instance.refresh_from_db()
        assert otp_instance.is_used is True

        response = client.post(reverse("auth-password-reset-confirm"), {
            "email": "owner@example.com", "otp": raw_otp,
            "new_password": "brand-new-pass-123", "confirm_new_password": "brand-new-pass-123",
        })
        assert response.status_code == 400
        owner.refresh_from_db()
        assert owner.check_password("str0ng-pass-123") is True

    def test_a_fresh_reset_otp_invalidates_the_previous_one(self, client, owner):
        first_otp, _ = PasswordResetOTP.create_for_user(owner)
        _, second_raw = PasswordResetOTP.create_for_user(owner)

        first_otp.refresh_from_db()
        assert first_otp.is_used is True

        response = client.post(reverse("auth-password-reset-confirm"), {
            "email": "owner@example.com", "otp": second_raw,
            "new_password": "brand-new-pass-123", "confirm_new_password": "brand-new-pass-123",
        })
        assert response.status_code == 200

    def test_password_reset_request_is_throttled_per_email(self, client, owner, throttled_rates):
        throttled_rates(auth_password_reset_request="2/min")

        for _ in range(2):
            client.post(reverse("auth-password-reset-request"), {"email": "owner@example.com"})
        blocked = client.post(reverse("auth-password-reset-request"), {"email": "owner@example.com"})

        assert blocked.status_code == 429


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
