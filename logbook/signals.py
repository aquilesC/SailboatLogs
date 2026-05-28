from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LogEntry, Trip
from .utils import fetch_weather_from_open_meteo
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

@receiver(post_save, sender=Trip)
def parse_trip_gpx(sender, instance, **kwargs):
    # Only parse if we have a file and the stats haven't been calculated yet
    if instance.gpx_file and (instance.total_distance is None or instance.max_speed is None):
        try:
            instance.gpx_file.open()
            gpx = gpxpy.parse(instance.gpx_file.file)
            
            moving_data = gpx.get_moving_data()
            
            # Convert distance (meters to nautical miles)
            total_distance_nm = moving_data.moving_distance * 0.000539957
            
            # Convert speed (m/s to knots)
            max_speed_knots = moving_data.max_speed * 1.94384 if moving_data.max_speed else 0.0
            
            instance.gpx_file.close()
            
            # Use update to avoid recursive save() calls
            Trip.objects.filter(pk=instance.pk).update(
                total_distance=round(total_distance_nm, 2),
                max_speed=round(max_speed_knots, 2)
            )
            
            # Update the in-memory instance as well
            instance.total_distance = round(total_distance_nm, 2)
            instance.max_speed = round(max_speed_knots, 2)
            
        except Exception as e:
            logger.error(f"Error parsing GPX file for Trip {instance.pk}: {e}")
