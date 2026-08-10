import hashlib
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cars.models import Car
from utils.Cloudinary import public_id_from_url

UPLOAD_TIMEOUT_SECONDS = 30
DEST_FOLDER = "cars"


class Command(BaseCommand):
    help = (
        "One-off: migrate Car.photo_url assets to the new Cloudinary account "
        "(see #48). Re-uploads each photo by its existing delivery URL to "
        "NEW_CLOUD_NAME under a cars/ folder, then updates photo_url once "
        "the re-upload is confirmed -- a failed row is left completely "
        "untouched, so nobody loses a photo they already uploaded. Never "
        "deletes anything from the old account; that's a separate, later "
        "step with its own grace period."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute", action="store_true",
            help="Actually perform the migration. Without this flag, only logs what would happen.",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Only process the first N not-yet-migrated cars -- for a small spot-check batch before a full run.",
        )

    def handle(self, *args, **options):
        execute = options["execute"]
        limit = options["limit"]

        cloud_name = settings.NEW_CLOUD_NAME
        api_key = settings.NEW_CLOUDINARY_API_KEY
        api_secret = settings.NEW_CLOUDINARY_API_SECRET
        if not (cloud_name and api_key and api_secret):
            raise CommandError("NEW_CLOUD_NAME / NEW_CLOUDINARY_API_KEY / NEW_CLOUDINARY_API_SECRET must all be set.")

        # Idempotent: a car whose photo_url already points at the new
        # account (e.g. left over from a previous partial run) is untouched,
        # not re-migrated on top of itself.
        already_marker = f"res.cloudinary.com/{cloud_name}/"
        candidates = Car.objects.exclude(photo_url__isnull=True).exclude(photo_url="")
        todo = [car for car in candidates if already_marker not in car.photo_url]
        already_done = candidates.count() - len(todo)
        if limit:
            todo = todo[:limit]

        self.stdout.write(
            f"{len(todo)} car(s) to migrate, {already_done} already on the new account "
            f"({'EXECUTING' if execute else 'DRY RUN — pass --execute to apply'})"
        )

        migrated = failed = 0
        for car in todo:
            if not public_id_from_url(car.photo_url):
                self.stderr.write(self.style.WARNING(f"car {car.id}: {car.photo_url} doesn't look like a Cloudinary URL, skipping"))
                failed += 1
                continue

            # car.id (a UUID, unique by construction) rather than the old
            # account's own basename -- Cloudinary upload overwrites an
            # existing asset at the same public_id by default, and nothing
            # guarantees two cars' old random basenames can't collide. This
            # makes that structurally impossible instead of just unlikely.
            new_public_id = f"{DEST_FOLDER}/{car.id}"

            if not execute:
                self.stdout.write(f"car {car.id}: would upload {car.photo_url} -> {new_public_id}")
                continue

            try:
                secure_url = _upload_by_url(cloud_name, api_key, api_secret, car.photo_url, new_public_id)
            except Exception as err:
                # Broad on purpose: a malformed/unexpected response (missing
                # secure_url, bad JSON) is exactly as "this row failed" as a
                # network error, and must never take down the whole run.
                self.stderr.write(self.style.ERROR(f"car {car.id}: upload failed ({err}), left untouched"))
                failed += 1
                continue

            car.photo_url = secure_url
            car.save(update_fields=["photo_url"])
            self.stdout.write(self.style.SUCCESS(f"car {car.id}: migrated -> {secure_url}"))
            migrated += 1

        self.stdout.write(f"Done. {migrated} migrated, {failed} failed, {already_done} already done.")


def _upload_by_url(cloud_name, api_key, api_secret, source_url, public_id):
    # Mirrors utils.Cloudinary._destroy()'s signing pattern: every
    # non-file/api_key param goes into the signature, sorted, joined, and
    # hashed with the secret appended.
    timestamp = str(int(time.time()))
    signing_params = {"public_id": public_id, "timestamp": timestamp}
    payload = "&".join(f"{key}={value}" for key, value in sorted(signing_params.items()))
    signature = hashlib.sha1(f"{payload}{api_secret}".encode()).hexdigest()

    response = requests.post(
        f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
        data={
            **signing_params,
            "api_key": api_key,
            "signature": signature,
            "file": source_url,
        },
        timeout=UPLOAD_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["secure_url"]
