import pytest
from django.conf import settings as django_settings
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from support.models import SupportRequest
from utils import Constants


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture(autouse=True)
def _reset_throttle_cache():
    # SupportRequestThrottle counts per test client IP — without this, the
    # 5/hour cap would trip partway through this test class.
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestSupportRequest:

    def test_visitor_can_submit_without_auth(self, client, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
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

    def test_attachments_are_emailed_without_touching_storage(
        self, client, django_capture_on_commit_callbacks, tmp_path, settings
    ):
        """
        Regression: attachments used to be written to MEDIA_ROOT and re-read by
        the Celery task. The worker pod has its own empty filesystem, so that
        read raised FileNotFoundError and the email — attachments and all —
        never went out. They now travel in the task payload instead.
        """
        settings.MEDIA_ROOT = str(tmp_path)
        upload = SimpleUploadedFile("photo.png", b"fake-bytes", content_type="image/png")

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(reverse("support-request"), {
                "name": "Alex",
                "email": "alex@example.com",
                "subject": Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT,
                "message": "See attached.",
                "attachments": [upload],
            }, format="multipart")
        assert response.status_code == 201

        sent = mail.outbox[0]
        assert len(sent.attachments) == 1
        assert sent.attachments[0][0] == "photo.png"
        assert sent.attachments[0][1] == b"fake-bytes"

        # Filenames are recorded; nothing was written to disk.
        assert SupportRequest.objects.get().attachment_names == ["photo.png"]
        assert list(tmp_path.iterdir()) == []

    def test_email_still_sends_when_the_worker_has_no_shared_filesystem(
        self, client, django_capture_on_commit_callbacks, tmp_path, settings
    ):
        """The exact production topology: nothing on disk for the worker to find."""
        import shutil

        settings.MEDIA_ROOT = str(tmp_path)
        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            client.post(reverse("support-request"), {
                "name": "Alex",
                "email": "alex@example.com",
                "subject": Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT,
                "message": "See attached.",
                "attachments": [SimpleUploadedFile("scan.pdf", b"%PDF-1.4", content_type="application/pdf")],
            }, format="multipart")

        # Wipe the media directory before the task runs, standing in for the
        # worker pod's separate (empty) filesystem.
        shutil.rmtree(tmp_path, ignore_errors=True)
        mail.outbox = []
        for callback in callbacks:
            callback()

        assert len(mail.outbox) == 1
        assert mail.outbox[0].attachments[0][0] == "scan.pdf"

    @pytest.mark.parametrize("filename,content_type", [
        ("payload.exe", "application/x-msdownload"),
        ("notes.txt", "text/plain"),
        ("archive.zip", "application/zip"),
        ("script.svg", "image/svg+xml"),
        ("photo.png", "application/x-msdownload"),
    ])
    def test_disallowed_attachment_types_rejected(self, client, filename, content_type):
        response = client.post(reverse("support-request"), {
            "name": "Alex",
            "email": "alex@example.com",
            "subject": Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT,
            "message": "Sketchy file.",
            "attachments": [SimpleUploadedFile(filename, b"x", content_type=content_type)],
        }, format="multipart")

        assert response.status_code == 400
        assert SupportRequest.objects.count() == 0
        assert mail.outbox == []

    def test_attachments_over_the_combined_size_cap_rejected(self, client):
        one_mb = b"x" * 1024 * 1024
        uploads = [
            SimpleUploadedFile(f"photo{i}.png", one_mb * 3, content_type="image/png")
            for i in range(Constants.SUPPORT_MAX_ATTACHMENTS)
        ]
        response = client.post(reverse("support-request"), {
            "name": "Alex",
            "email": "alex@example.com",
            "subject": Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT,
            "message": "Way too much.",
            "attachments": uploads,
        }, format="multipart")

        assert response.status_code == 400
        assert SupportRequest.objects.count() == 0

    def test_throttled_after_rate_limit(self, client):
        limit = int(django_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["support_request"].split("/")[0])

        for _ in range(limit):
            response = client.post(reverse("support-request"), {
                "name": "Alex",
                "email": "alex@example.com",
                "subject": Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT,
                "message": "Spam attempt.",
            })
            assert response.status_code == 201

        response = client.post(reverse("support-request"), {
            "name": "Alex",
            "email": "alex@example.com",
            "subject": Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT,
            "message": "One too many.",
        })
        assert response.status_code == 429

    def test_too_many_attachments_rejected(self, client):
        uploads = [
            SimpleUploadedFile(f"f{i}.png", b"x", content_type="image/png")
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
