from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=50, unique=True, help_text="Phone number for Twilio WhatsApp matching (e.g., +1234567890)")

    def __str__(self):
        return f"{self.user.username} Profile"

class Boat(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    shared_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='shared_boats', blank=True)

    def __str__(self):
        return self.name

class Trip(models.Model):
    boat = models.ForeignKey(Boat, on_delete=models.CASCADE, related_name='trips')
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    gpx_file = models.FileField(upload_to='gpx_files/', null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    
    # These fields will be populated in Phase 4
    total_distance = models.FloatField(null=True, blank=True, help_text="Total distance in nautical miles or km")
    max_speed = models.FloatField(null=True, blank=True, help_text="Max speed in knots or km/h")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.boat.name}-{self.title}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class LogEntry(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='log_entries')
    entry_text = models.TextField()
    timestamp = models.DateTimeField(help_text="Parsed from Twilio payload")
    
    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Weather
    wind_speed = models.FloatField(null=True, blank=True, help_text="Wind speed (e.g., knots)")
    wind_direction = models.FloatField(null=True, blank=True, help_text="Wind direction in degrees")
    temperature = models.FloatField(null=True, blank=True, help_text="Temperature in Celsius")
    
    tags = models.ManyToManyField(Tag, related_name='log_entries', blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.trip.title} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
