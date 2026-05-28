"""
Management command to re-process existing photos.

Generates thumbnails and extracts EXIF datetime for all LogEntryPhoto records
that are missing them.
"""
import logging

from django.core.management.base import BaseCommand
from logbook.models import LogEntryPhoto
from logbook.utils import extract_exif_datetime, generate_thumbnail

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Re-process existing photos: generate thumbnails and extract EXIF datetime'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-process all photos, even those that already have thumbnails/EXIF data',
        )

    def handle(self, *args, **options):
        force = options['force']

        if force:
            photos = LogEntryPhoto.objects.all()
        else:
            # Only process photos missing thumbnail or taken_at
            from django.db.models import Q
            photos = LogEntryPhoto.objects.filter(
                Q(thumbnail='') | Q(taken_at__isnull=True)
            )

        total = photos.count()
        self.stdout.write(f"Found {total} photo(s) to process.")

        processed = 0
        errors = 0

        for photo in photos:
            if not photo.image:
                self.stdout.write(self.style.WARNING(
                    f"  Skipping photo {photo.pk}: no image file"
                ))
                continue

            update_fields = []

            # Extract EXIF datetime
            if force or not photo.taken_at:
                try:
                    exif_dt = extract_exif_datetime(photo.image)
                    if exif_dt:
                        photo.taken_at = exif_dt
                        update_fields.append('taken_at')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"  EXIF error for photo {photo.pk}: {e}"
                    ))

            # Generate thumbnail
            if force or not photo.thumbnail:
                try:
                    thumb_file = generate_thumbnail(photo.image, size=(150, 150))
                    if thumb_file:
                        photo.thumbnail.save(thumb_file.name, thumb_file, save=False)
                        update_fields.append('thumbnail')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"  Thumbnail error for photo {photo.pk}: {e}"
                    ))

            if update_fields:
                photo.save(update_fields=update_fields)
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Photo {photo.pk}: updated {', '.join(update_fields)}"
                ))
                processed += 1
            else:
                self.stdout.write(f"  - Photo {photo.pk}: nothing to update")

        self.stdout.write(f"\nDone. Processed: {processed}, Errors: {errors}, Total: {total}")
