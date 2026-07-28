import uuid

from django.conf import settings
from django.db import models

from utils import Constants


def support_attachment_path(instance, filename):
    return f"support_attachments/{instance.support_request_id}/{filename}"


class SupportRequest(models.Model):
    """
    A contact-us submission — covers account activation issues, general
    help, and unauthenticated visitors. `user` is set when submitted while
    logged in, but the endpoint itself is open to anyone.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="support_requests",
    )

    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=30, choices=Constants.SUPPORT_SUBJECTS, default=Constants.SUPPORT_SUBJECT_GENERAL_ACCOUNT)
    custom_subject = models.CharField(max_length=150, blank=True)
    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.display_subject} — {self.email}"

    @property
    def display_subject(self):
        if self.subject == Constants.SUPPORT_SUBJECT_OTHER and self.custom_subject:
            return self.custom_subject
        return self.get_subject_display()


class SupportAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_request = models.ForeignKey(SupportRequest, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=support_attachment_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
