import hashlib
import logging
import re
from urllib.parse import urlparse

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Matches the delivery URL shape produced by the browser's unsigned upload in
# CarForm.jsx: .../upload/<transformations>/v<version>/<public_id>.<format>.
# public_id can itself contain slashes (Cloudinary folders), so it's captured
# greedily up to the final extension.
_PUBLIC_ID_RE = re.compile(r"/upload/(?:[^/]+/)?v\d+/(?P<public_id>.+)\.[a-zA-Z0-9]+$")

DESTROY_TIMEOUT_SECONDS = 10


def _public_id_from_url(url: str) -> str | None:
    match = _PUBLIC_ID_RE.search(url)
    return match.group("public_id") if match else None


def _credentials_from_settings() -> tuple[str, str, str] | None:
    """
    Parses the standard `cloudinary://<api_key>:<api_secret>@<cloud_name>`
    format (CLOUDINARY_URL) that Cloudinary's own SDKs read — matches what's
    already in local dev .env files, so no separate credential shape to keep
    in sync. Returns None if unset or unparseable.
    """
    raw = getattr(settings, "CLOUDINARY_URL", "")
    if not raw:
        return None

    parsed = urlparse(raw)
    if parsed.scheme != "cloudinary" or not (parsed.username and parsed.password and parsed.hostname):
        return None
    return parsed.hostname, parsed.username, parsed.password


def delete_photos(urls: list[str]) -> None:
    """
    Best-effort delete of Cloudinary-hosted photos by their delivery URL.
    No-ops (with a warning) if CLOUDINARY_URL isn't configured, and never
    raises — a failed cleanup shouldn't block the account deletion it's part
    of.
    """
    urls = [u for u in urls if u]
    if not urls:
        return

    credentials = _credentials_from_settings()
    if credentials is None:
        logger.warning("Skipping Cloudinary cleanup for %d photo(s): CLOUDINARY_URL not configured", len(urls))
        return
    cloud_name, api_key, api_secret = credentials

    for url in urls:
        public_id = _public_id_from_url(url)
        if not public_id:
            logger.warning("Could not parse a Cloudinary public_id from %s; skipping", url)
            continue
        _destroy(cloud_name, api_key, api_secret, public_id)


def _destroy(cloud_name: str, api_key: str, api_secret: str, public_id: str) -> None:
    import time

    timestamp = str(int(time.time()))
    # Cloudinary's signing scheme: sort every non-file param, join as
    # "key=value&...", append the API secret, then SHA1 it.
    signature = hashlib.sha1(f"public_id={public_id}&timestamp={timestamp}{api_secret}".encode()).hexdigest()

    try:
        response = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/destroy",
            data={
                "public_id": public_id,
                "timestamp": timestamp,
                "api_key": api_key,
                "signature": signature,
            },
            timeout=DESTROY_TIMEOUT_SECONDS,
        )
        if not response.ok:
            logger.warning("Cloudinary destroy failed for %s: %s %s", public_id, response.status_code, response.text)
    except requests.RequestException:
        logger.warning("Cloudinary destroy request errored for %s", public_id, exc_info=True)
