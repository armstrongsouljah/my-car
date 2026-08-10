from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from cars.models import Car


class Command(BaseCommand):
    help = (
        "One-off: backfill Car.photo_url with the default photo for cars "
        "that don't have one (see #94). Car.save() already covers every "
        "*new* car going forward -- this is only for rows that predate that."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute", action="store_true",
            help="Actually perform the backfill. Without this flag, only logs what would happen.",
        )

    def handle(self, *args, **options):
        if not settings.DEFAULT_PHOTO_URL:
            self.stderr.write(self.style.ERROR("DEFAULT_PHOTO_URL must be set."))
            return

        qs = Car.objects.filter(Q(photo_url__isnull=True) | Q(photo_url=""))
        count = qs.count()

        if not options["execute"]:
            self.stdout.write(f"{count} car(s) without a photo — DRY RUN, pass --execute to apply")
            return

        updated = qs.update(photo_url=settings.DEFAULT_PHOTO_URL)
        self.stdout.write(self.style.SUCCESS(f"Backfilled {updated} car(s) with the default photo."))
