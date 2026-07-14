import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User, EmailVerificationOTP


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
