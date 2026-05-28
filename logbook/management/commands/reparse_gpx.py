"""
Management command to re-parse all existing GPX files.

Updates track_points to include all available data (elevation, time, speed, etc.)
instead of the old [lat, lng] format.
"""
import gpxpy
import logging

from django.core.management.base import BaseCommand
from logbook.models import GPXFile
from logbook.signals import _aggregate_trip_stats

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Re-parse all GPX files to store full trackpoint data (elevation, time, speed, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        gpx_files = GPXFile.objects.all()
        total = gpx_files.count()

        self.stdout.write(f"Found {total} GPX file(s) to re-parse.")

        updated = 0
        errors = 0
        affected_trips = set()

        for gpx_record in gpx_files:
            if not gpx_record.file:
                self.stdout.write(self.style.WARNING(
                    f"  Skipping GPXFile {gpx_record.pk}: no file on disk"
                ))
                continue

            try:
                gpx_record.file.open('rb')
                gpx = gpxpy.parse(gpx_record.file.file)
                gpx_record.file.close()

                # Extract all track points with all available data
                track_points = []
                for track in gpx.tracks:
                    for segment in track.segments:
                        for point in segment.points:
                            pt = {
                                'lat': float(point.latitude),
                                'lng': float(point.longitude),
                            }
                            if point.elevation is not None:
                                pt['ele'] = round(float(point.elevation), 1)
                            if point.time is not None:
                                pt['time'] = point.time.isoformat()
                            if point.speed is not None:
                                pt['speed'] = round(float(point.speed), 2)
                            if point.horizontal_dilution is not None:
                                pt['hdop'] = round(float(point.horizontal_dilution), 1)
                            if point.vertical_dilution is not None:
                                pt['vdop'] = round(float(point.vertical_dilution), 1)
                            if point.position_dilution is not None:
                                pt['pdop'] = round(float(point.position_dilution), 1)
                            track_points.append(pt)

                # Re-calculate distance and speed
                moving_data = gpx.get_moving_data()
                distance_nm = moving_data.moving_distance * 0.000539957 if moving_data.moving_distance else 0.0
                max_speed_kn = moving_data.max_speed * 1.94384 if moving_data.max_speed else 0.0

                old_points = len(gpx_record.track_points) if gpx_record.track_points else 0
                new_points = len(track_points)
                has_time = any('time' in pt for pt in track_points)

                if dry_run:
                    self.stdout.write(
                        f"  [DRY RUN] GPXFile {gpx_record.pk} "
                        f"({gpx_record.original_filename}): "
                        f"{old_points} → {new_points} points, "
                        f"timestamps: {'yes' if has_time else 'no'}"
                    )
                else:
                    GPXFile.objects.filter(pk=gpx_record.pk).update(
                        track_points=track_points,
                        distance_nm=round(distance_nm, 2),
                        max_speed_kn=round(max_speed_kn, 2),
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ GPXFile {gpx_record.pk} "
                        f"({gpx_record.original_filename}): "
                        f"{new_points} points, "
                        f"timestamps: {'yes' if has_time else 'no'}"
                    ))
                    affected_trips.add(gpx_record.trip_id)

                updated += 1

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(
                    f"  ✗ GPXFile {gpx_record.pk} ({gpx_record.original_filename}): {e}"
                ))

        # Re-aggregate trip stats
        if not dry_run:
            from logbook.models import Trip
            for trip_id in affected_trips:
                try:
                    trip = Trip.objects.get(pk=trip_id)
                    _aggregate_trip_stats(trip)
                except Trip.DoesNotExist:
                    pass

        self.stdout.write(
            f"\nDone. Updated: {updated}, Errors: {errors}, "
            f"Trips affected: {len(affected_trips)}"
        )
