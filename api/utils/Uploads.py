"""
Shared validation for user-supplied files.

Both upload surfaces (support attachments, inspection reports) accept the same
narrow set: images and PDFs. Extension and declared content type both have to
pass — the browser-supplied content type is trivially spoofed on its own, and
the extension is what most downstream readers (mail clients, the OS) actually
act on, so neither is sufficient alone.
"""
from django.core.exceptions import ValidationError

from utils import Constants


def _extension_of(filename):
    name = (filename or "").lower()
    return name[name.rfind("."):] if "." in name else ""


def is_allowed_upload(filename, content_type=None):
    if _extension_of(filename) not in Constants.ALLOWED_UPLOAD_EXTENSIONS:
        return False
    # Django leaves content_type unset for some clients; the extension check
    # above already ran, so only reject a type that is present and disallowed.
    if content_type and content_type.lower() not in Constants.ALLOWED_UPLOAD_CONTENT_TYPES:
        return False
    return True


def allowed_types_message():
    return "Allowed types: " + ", ".join(e.lstrip(".") for e in Constants.ALLOWED_UPLOAD_EXTENSIONS) + "."


def validate_upload_type(uploaded_file):
    """Model/serializer-field validator — raises Django's ValidationError."""
    if not is_allowed_upload(uploaded_file.name, getattr(uploaded_file, "content_type", None)):
        raise ValidationError(f'"{uploaded_file.name}" is not an accepted file type. {allowed_types_message()}')


def validate_history_import_upload(uploaded_file):
    """See #103 — a PDF/.docx/.xlsx the owner already has, not a photo."""
    content_type = getattr(uploaded_file, "content_type", None)
    if _extension_of(uploaded_file.name) not in Constants.HISTORY_IMPORT_UPLOAD_EXTENSIONS or (
        content_type and content_type.lower() not in Constants.HISTORY_IMPORT_UPLOAD_CONTENT_TYPES
    ):
        raise ValidationError(f'"{uploaded_file.name}" is not an accepted file type. Upload a PDF, Word (.docx), or Excel (.xlsx) file.')
    if uploaded_file.size > Constants.HISTORY_IMPORT_MAX_UPLOAD_BYTES:
        max_mb = Constants.HISTORY_IMPORT_MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ValidationError(f"File is too large — max {max_mb}MB.")
