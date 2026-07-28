from rest_framework.permissions import AllowAny
from rest_framework import status

from utils.Views import SmartAPIView
from utils.Exception import CustomValidation
from utils import Constants

from support.models import SupportRequest, SupportAttachment
from support.serializers import SupportRequestSerializer


class SupportRequestView(SmartAPIView):
    """
    POST — contact-us submission (multipart/form-data with optional
    `attachments` file fields). Open to visitors as well as logged-in users.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SupportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        files = request.FILES.getlist("attachments")
        if len(files) > Constants.SUPPORT_MAX_ATTACHMENTS:
            raise CustomValidation(
                f"Please attach at most {Constants.SUPPORT_MAX_ATTACHMENTS} files.",
                field="attachments",
            )
        max_bytes = Constants.SUPPORT_MAX_ATTACHMENT_SIZE_MB * 1024 * 1024
        for uploaded_file in files:
            if uploaded_file.size > max_bytes:
                raise CustomValidation(
                    f'"{uploaded_file.name}" is larger than {Constants.SUPPORT_MAX_ATTACHMENT_SIZE_MB}MB.',
                    field="attachments",
                )

        support_request = SupportRequest.objects.create(
            user=request.user if request.user.is_authenticated else None,
            name=data["name"],
            email=data["email"],
            subject=data["subject"],
            custom_subject=data.get("custom_subject", ""),
            message=data["message"],
        )
        for uploaded_file in files:
            SupportAttachment.objects.create(support_request=support_request, file=uploaded_file)

        from tasks import send_support_request_email_task

        send_support_request_email_task.delay(support_request_id=str(support_request.id))

        return self.respond_with(
            "Thanks — we've got your message and will get back to you soon.",
            status_code=status.HTTP_201_CREATED,
        )
