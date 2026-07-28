import pytest
from django.conf import settings as django_settings
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from support.models import SupportRequest
from utils import Constants


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
class TestSupportRequest:

    def test_visitor_can_submit_without_auth(self, client):
        response = client.post(reverse("support-request"), {
            "name": "Alex Visitor",
            "email": "alex@example.com",
            "subject": Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT,
            "message": "I can't activate my account.",
        })
        assert response.status_code == 201

        support_request = SupportRequest.objects.get()
        assert support_request.user is None
        assert support_request.email == "alex@example.com"

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == [django_settings.DEFAULT_FROM_EMAIL]
        assert sent.reply_to == ["alex@example.com"]

    def test_logged_in_user_is_attached(self, client):
        user = User.objects.create_user(email="owner@example.com", password="str0ng-pass-123")
        client.force_authenticate(user=user)

        response = client.post(reverse("support-request"), {
            "name": "Owner",
            "email": "owner@example.com",
            "subject": Constants.SUPPORT_SUBJECT_APP_INQUIRY,
            "message": "How do I export my data?",
        })
        assert response.status_code == 201
        assert SupportRequest.objects.get().user_id == user.id

    def test_other_subject_requires_custom_subject(self, client):
        response = client.post(reverse("support-request"), {
            "name": "Alex",
            "email": "alex@example.com",
            "subject": Constants.SUPPORT_SUBJECT_OTHER,
            "message": "Something specific.",
        })
        assert response.status_code == 400
        assert "custom_subject" in response.data

    def test_other_subject_with_custom_subject_succeeds(self, client):
        response = client.post(reverse("support-request"), {
            "name": "Alex",
            "email": "alex@example.com",
            "subject": Constants.SUPPORT_SUBJECT_OTHER,
            "custom_subject": "Billing question",
            "message": "Something specific.",
        })
        assert response.status_code == 201
        assert SupportRequest.objects.get().display_subject == "Billing question"

    def test_attachments_are_saved_and_emailed(self, client):
        upload = SimpleUploadedFile("photo.png", b"fake-bytes", content_type="image/png")
        response = client.post(reverse("support-request"), {
            "name": "Alex",
            "email": "alex@example.com",
            "subject": Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT,
            "message": "See attached.",
            "attachments": [upload],
        }, format="multipart")
        assert response.status_code == 201

        support_request = SupportRequest.objects.get()
        assert support_request.attachments.count() == 1

        sent = mail.outbox[0]
        assert len(sent.attachments) == 1
        assert sent.attachments[0][0] == "photo.png"

    def test_too_many_attachments_rejected(self, client):
        uploads = [
            SimpleUploadedFile(f"f{i}.txt", b"x", content_type="text/plain")
            for i in range(Constants.SUPPORT_MAX_ATTACHMENTS + 1)
        ]
        response = client.post(reverse("support-request"), {
            "name": "Alex",
            "email": "alex@example.com",
            "subject": Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT,
            "message": "Too many files.",
            "attachments": uploads,
        }, format="multipart")
        assert response.status_code == 400
        assert SupportRequest.objects.count() == 0
