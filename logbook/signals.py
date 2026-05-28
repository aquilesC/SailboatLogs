from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LogEntry
from .utils import fetch_weather_from_open_meteo

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
