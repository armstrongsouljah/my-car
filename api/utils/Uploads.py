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


def validate_upload_size(uploaded_file, max_size_mb):
    """Model/serializer-field validator — support attachments already had a
    size cap (SUPPORT_MAX_ATTACHMENT_SIZE_MB, enforced in support/views.py
    since they never touch a model field); inspection reports had none at
    all. A plain top-level function (not a closure) bound per-field via
    functools.partial — Django's migration serializer can't serialize a
    closure, but it can serialize a partial over an importable function
    with plain-value args."""
    max_bytes = max_size_mb * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValidationError(f'"{uploaded_file.name}" is larger than {max_size_mb}MB.')
