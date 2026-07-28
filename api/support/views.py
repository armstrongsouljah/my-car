from base64 import b64encode

from django.db import transaction
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.throttling import UserRateThrottle

from utils.Views import SmartAPIView
from utils.Exception import CustomValidation
from utils.Uploads import allowed_types_message, is_allowed_upload
from utils import Constants

from support.models import SupportRequest
from support.serializers import SupportRequestSerializer


class SupportRequestThrottle(UserRateThrottle):
    """AllowAny + file uploads is an easy bot target — cap submissions per user/IP."""
    scope = "support_request"


class SupportRequestView(SmartAPIView):
    """
    POST — contact-us submission (multipart/form-data with optional
    `attachments` file fields). Open to visitors as well as logged-in users.
    """
    permission_classes = [AllowAny]
    throttle_classes = [SupportRequestThrottle]

    def post(self, request):
        serializer = SupportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        attachments = self.read_attachments(request.FILES.getlist("attachments"))

        with transaction.atomic():
            support_request = SupportRequest.objects.create(
                user=request.user if request.user.is_authenticated else None,
                name=data["name"],
                email=data["email"],
                subject=data["subject"],
                custom_subject=data.get("custom_subject", ""),
                message=data["message"],
                attachment_names=[name for name, _, _ in attachments],
            )

            from tasks import send_support_request_email_task

            # Attachments ride along in the task payload rather than going to
            # storage: the API pod and the Celery worker have separate
            # filesystems, so anything written here is unreadable there.
            payload = [
                {"name": name, "content_type": content_type, "content_b64": b64encode(content).decode()}
                for name, content, content_type in attachments
            ]
            transaction.on_commit(
                lambda: send_support_request_email_task.delay(
                    support_request_id=str(support_request.id), attachments=payload
                )
            )

        return self.respond_with(
            "Thanks — we've got your message and will get back to you soon.",
            status_code=status.HTTP_201_CREATED,
        )

    def read_attachments(self, files):
        """Validate the uploads and pull them into memory as (name, bytes, type)."""
        if len(files) > Constants.SUPPORT_MAX_ATTACHMENTS:
            raise CustomValidation(
                f"Please attach at most {Constants.SUPPORT_MAX_ATTACHMENTS} files.",
                field="attachments",
            )

        max_bytes = Constants.SUPPORT_MAX_ATTACHMENT_SIZE_MB * 1024 * 1024
        max_total_bytes = Constants.SUPPORT_MAX_ATTACHMENT_TOTAL_MB * 1024 * 1024

        for uploaded_file in files:
            if uploaded_file.size > max_bytes:
                raise CustomValidation(
                    f'"{uploaded_file.name}" is larger than {Constants.SUPPORT_MAX_ATTACHMENT_SIZE_MB}MB.',
                    field="attachments",
                )
            if not is_allowed_upload(uploaded_file.name, getattr(uploaded_file, "content_type", None)):
                raise CustomValidation(
                    f'"{uploaded_file.name}" is not an accepted file type. {allowed_types_message()}',
                    field="attachments",
                )

        if sum(f.size for f in files) > max_total_bytes:
            raise CustomValidation(
                f"Attachments come to more than {Constants.SUPPORT_MAX_ATTACHMENT_TOTAL_MB}MB in total.",
                field="attachments",
            )

        return [
            (uploaded_file.name.rsplit("/", 1)[-1], uploaded_file.read(), uploaded_file.content_type)
            for uploaded_file in files
        ]
