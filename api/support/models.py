import uuid

from django.conf import settings
from django.db import models

from utils import Constants


def support_attachment_path(instance, filename):
    """
    Dead code, kept only because migration 0001_initial still references it by
    import path. Attachments are no longer written to storage — see migration
    0002_drop_attachment_storage.
    """
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

    # Attachment *contents* are never stored — they go out on the notification
    # email and are then dropped. Only the filenames are kept, so the support
    # inbox thread and this record can be matched up later.
    attachment_names = models.JSONField(default=list, blank=True)

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
