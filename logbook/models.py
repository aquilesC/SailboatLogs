import uuid
import os

from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    phone_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Phone number for Twilio WhatsApp matching (e.g., +1234567890)",
    )

    def __str__(self):
        return f"{self.user.username} Profile"


class Boat(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    boat_model = models.CharField(
        max_length=255, blank=True, help_text="Boat model (e.g., Beneteau Oceanis 38.1)"
    )
    homeport = models.CharField(
        max_length=255, blank=True, help_text="Home port / marina"
    )
    mmsi_registration = models.CharField(
        max_length=100, blank=True, help_text="MMSI number or registration ID"
    )
    shared_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="shared_boats", blank=True
    )

    def __str__(self):
        return self.name


class Trip(models.Model):
    boat = models.ForeignKey(Boat, on_delete=models.CASCADE, related_name="trips")
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    gpx_file = models.FileField(upload_to="gpx_files/", null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    share_slug = models.SlugField(
        unique=True, blank=True, help_text="Randomized slug for public sharing links"
    )

    # These fields will be populated in Phase 4
    total_distance = models.FloatField(
        null=True, blank=True, help_text="Total distance in nautical miles or km"
    )
    max_speed = models.FloatField(
        null=True, blank=True, help_text="Max speed in knots or km/h"
    )

    def _generate_share_slug(self):
        """Generate a short random slug for public sharing."""
        return uuid.uuid4().hex[:12]

    def regenerate_share_slug(self):
        """Regenerate the share_slug and save."""
        self.share_slug = self._generate_share_slug()
        self.save(update_fields=["share_slug"])

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.boat.name}-{self.title}")
            slug = base_slug
            counter = 1
            while Trip.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if not self.share_slug:
            self.share_slug = self._generate_share_slug()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class LogEntry(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_logs",
    )
    boat = models.ForeignKey(
        Boat,
        on_delete=models.CASCADE,
        related_name="log_entries",
        null=True,
        blank=True,
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="log_entries",
        null=True,
        blank=True,
    )
    entry_text = models.TextField(blank=True)
    timestamp = models.DateTimeField(help_text="Parsed from Twilio payload")

    # Location
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Weather
    wind_speed = models.FloatField(
        null=True, blank=True, help_text="Wind speed (e.g., knots)"
    )
    wind_direction = models.FloatField(
        null=True, blank=True, help_text="Wind direction in degrees"
    )
    temperature = models.FloatField(
        null=True, blank=True, help_text="Temperature in Celsius"
    )

    tags = models.ManyToManyField(Tag, related_name="log_entries", blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        title = self.trip.title if self.trip else self.boat.name
        return f"{title} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class GPXFile(models.Model):
    """A GPX track file attached to a trip. Multiple GPX files per trip are supported."""

    SOURCE_CHOICES = [
        ("web", "Web Upload"),
        ("whatsapp", "WhatsApp"),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="gpx_files")
    file = models.FileField(upload_to="gpx_files/")
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="web")

    # Parsed data (populated by signal on save)
    track_points = models.JSONField(
        default=list, blank=True, help_text="Parsed [[lat, lng], ...] array"
    )
    distance_nm = models.FloatField(
        null=True, blank=True, help_text="Distance in nautical miles"
    )
    max_speed_kn = models.FloatField(
        null=True, blank=True, help_text="Max speed in knots"
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.trip.title})"


def _photo_thumbnail_path(instance, filename):
    """Upload thumbnail alongside the original, in a 'thumbs/' subdirectory."""
    base, ext = os.path.splitext(filename)
    return f"log_photos/thumbs/{base}_thumb{ext}"


class LogEntryPhoto(models.Model):
    """A photo attached to a log entry. Can arrive via WhatsApp or web upload."""

    SOURCE_CHOICES = [
        ("web", "Web Upload"),
        ("whatsapp", "WhatsApp"),
    ]

    log_entry = models.ForeignKey(
        LogEntry, on_delete=models.CASCADE, related_name="photos"
    )
    image = models.ImageField(upload_to="log_photos/%Y/%m/")
    thumbnail = models.ImageField(
        upload_to=_photo_thumbnail_path,
        blank=True,
        help_text="Auto-generated 150px thumbnail for map markers",
    )
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    taken_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Photo capture time from EXIF, falls back to log entry timestamp",
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="web")

    class Meta:
        ordering = ["uploaded_at"]

    @property
    def effective_timestamp(self):
        """Return taken_at if available, otherwise the parent log entry's timestamp."""
        return self.taken_at or self.log_entry.timestamp

    def __str__(self):
        return f"Photo for {self.log_entry}"
