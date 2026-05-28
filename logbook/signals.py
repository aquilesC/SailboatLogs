from django.db.models.signals import post_save
from django.db.models import Sum, Max
from django.dispatch import receiver
from .models import LogEntry, GPXFile, LogEntryPhoto
from .utils import fetch_weather_from_open_meteo, extract_exif_datetime, generate_thumbnail
import gpxpy
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=LogEntry)
def enrich_log_entry_weather(sender, instance, created, **kwargs):
    # Only fetch weather upon creation and if coordinates exist
    if created and instance.latitude and instance.longitude:
        weather_data = fetch_weather_from_open_meteo(instance.latitude, instance.longitude)
        
        if weather_data:
            update_fields = []
            
            if weather_data.get('wind_speed') is not None:
                instance.wind_speed = weather_data['wind_speed']
                update_fields.append('wind_speed')
                
            if weather_data.get('wind_direction') is not None:
                instance.wind_direction = weather_data['wind_direction']
                update_fields.append('wind_direction')
                
            if weather_data.get('temperature') is not None:
                instance.temperature = weather_data['temperature']
                update_fields.append('temperature')
                
            if update_fields:
                instance.save(update_fields=update_fields)


@receiver(post_save, sender=GPXFile)
def parse_gpx_file(sender, instance, created, **kwargs):
    """Parse a GPXFile on creation: extract track points, distance, and speed."""
    if not created:
        return

    if not instance.file:
        return

    try:
        instance.file.open('rb')
        gpx = gpxpy.parse(instance.file.file)
        instance.file.close()

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

        # Calculate distance and speed
        moving_data = gpx.get_moving_data()
        distance_nm = moving_data.moving_distance * 0.000539957 if moving_data.moving_distance else 0.0
        max_speed_kn = moving_data.max_speed * 1.94384 if moving_data.max_speed else 0.0

        # Update the GPXFile record (avoid recursive signal with update())
        GPXFile.objects.filter(pk=instance.pk).update(
            track_points=track_points,
            distance_nm=round(distance_nm, 2),
            max_speed_kn=round(max_speed_kn, 2),
        )

        # Update in-memory instance
        instance.track_points = track_points
        instance.distance_nm = round(distance_nm, 2)
        instance.max_speed_kn = round(max_speed_kn, 2)

        # Re-aggregate trip-level stats from all GPX files
        _aggregate_trip_stats(instance.trip)

    except Exception as e:
        logger.error(f"Error parsing GPX file {instance.pk} ({instance.original_filename}): {e}")


def _aggregate_trip_stats(trip):
    """Sum distance and take max speed across all GPXFile records for a trip."""
    from .models import Trip

    stats = trip.gpx_files.aggregate(
        total_distance=Sum('distance_nm'),
        top_speed=Max('max_speed_kn'),
    )

    Trip.objects.filter(pk=trip.pk).update(
        total_distance=stats['total_distance'] or None,
        max_speed=stats['top_speed'] or None,
    )


@receiver(post_save, sender=LogEntryPhoto)
def enrich_photo(sender, instance, created, **kwargs):
    """On creation, extract EXIF datetime and generate a thumbnail."""
    if not created:
        return

    if not instance.image:
        return

    update_fields = []

    # 1. Extract EXIF datetime
    try:
        from logbook.utils import extract_exif_datetime, generate_thumbnail, resize_image
        exif_dt = extract_exif_datetime(instance.image)
        if exif_dt:
            instance.taken_at = exif_dt
            update_fields.append('taken_at')
    except Exception as e:
        logger.warning(f"Could not extract EXIF datetime for photo {instance.pk}: {e}")

    # 1b. Resize the main image down to 1920px to save storage, preserving EXIF
    try:
        resized_file = resize_image(instance.image, max_size=1920)
        if resized_file:
            instance.image.save(resized_file.name, resized_file, save=False)
            update_fields.append('image')
    except Exception as e:
        logger.warning(f"Could not resize original image for photo {instance.pk}: {e}")

    # 2. Generate thumbnail
    try:
        thumb_file = generate_thumbnail(instance.image, size=(150, 150))
        if thumb_file:
            instance.thumbnail.save(thumb_file.name, thumb_file, save=False)
            update_fields.append('thumbnail')
    except Exception as e:
        logger.warning(f"Could not generate thumbnail for photo {instance.pk}: {e}")

    if update_fields:
        instance.save(update_fields=update_fields)
