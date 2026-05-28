import os
import requests
import logging
from io import BytesIO
from datetime import datetime, timezone, timedelta

from PIL import Image
from PIL.ExifTags import Base as ExifBase
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def fetch_weather_from_open_meteo(latitude, longitude):
    """
    Fetches current weather from Open-Meteo API based on coordinates.
    Returns a dictionary with wind_speed, wind_direction, and temperature.
    """
    try:
        # Open-Meteo requires coordinates as floats
        lat = float(latitude)
        lon = float(longitude)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current_weather": "true"}

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "current_weather" in data:
            current = data["current_weather"]
            return {
                "wind_speed": current.get("windspeed"),
                "wind_direction": current.get("winddirection"),
                "temperature": current.get("temperature"),
            }
        return {}
    except Exception as e:
        logger.error(f"Error fetching weather from Open-Meteo: {e}")
        return {}


def extract_exif_datetime(image_field):
    """
    Extract the capture datetime from an image's EXIF data.

    Tries DateTimeOriginal, DateTimeDigitized, then DateTime.
    Handles OffsetTimeOriginal / OffsetTime for timezone-aware results.
    Returns a timezone-aware datetime or None.
    """
    try:
        image_field.open("rb")
        img = Image.open(image_field.file)
        exif_data = img.getexif()
        image_field.close()

        if not exif_data:
            return None

        # Also check the EXIF IFD for DateTimeOriginal/DateTimeDigitized
        exif_ifd = exif_data.get_ifd(ExifBase.ExifOffset)

        # Priority: DateTimeOriginal > DateTimeDigitized > DateTime
        dt_str = None
        offset_str = None

        if exif_ifd.get(ExifBase.DateTimeOriginal):
            dt_str = exif_ifd[ExifBase.DateTimeOriginal]
            offset_str = exif_ifd.get(ExifBase.OffsetTimeOriginal)
        elif exif_ifd.get(ExifBase.DateTimeDigitized):
            dt_str = exif_ifd[ExifBase.DateTimeDigitized]
            offset_str = exif_ifd.get(ExifBase.OffsetTimeDigitized)
        elif exif_data.get(ExifBase.DateTime):
            dt_str = exif_data[ExifBase.DateTime]
            offset_str = exif_ifd.get(ExifBase.OffsetTime) or exif_data.get(
                ExifBase.OffsetTime
            )

        if not dt_str:
            return None

        # Parse "YYYY:MM:DD HH:MM:SS" format
        dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")

        # Apply timezone offset if available (format: "+02:00" or "-05:00")
        if offset_str:
            try:
                sign = 1 if offset_str[0] == "+" else -1
                parts = offset_str[1:].split(":")
                offset_hours = int(parts[0])
                offset_minutes = int(parts[1]) if len(parts) > 1 else 0
                tz = timezone(
                    timedelta(hours=sign * offset_hours, minutes=sign * offset_minutes)
                )
                dt = dt.replace(tzinfo=tz)
            except (ValueError, IndexError):
                # Fall back to UTC if offset parsing fails
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            # No offset info — assume UTC
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except Exception as e:
        logger.warning(f"Error extracting EXIF datetime: {e}")
        return None


def generate_thumbnail(image_field, size=(150, 150)):
    """
    Generate a center-cropped JPEG thumbnail from an image field.

    Returns a ContentFile ready to be saved, or None on failure.
    """
    try:
        image_field.open("rb")
        img = Image.open(image_field.file)

        # Handle EXIF orientation
        try:
            from PIL import ImageOps

            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Convert to RGB if necessary (e.g., RGBA PNGs)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Center-crop to square, then resize
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
        img = img.resize(size, Image.LANCZOS)

        # Save to buffer
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80, optimize=True)
        buf.seek(0)

        image_field.close()

        # Derive filename from original
        original_name = os.path.basename(image_field.name)
        base, _ = os.path.splitext(original_name)
        thumb_name = f"{base}_thumb.jpg"

        return ContentFile(buf.read(), name=thumb_name)

    except Exception as e:
        logger.warning(f"Error generating thumbnail: {e}")
        try:
            image_field.close()
        except Exception:
            pass
        return None


def resize_image(image_field, max_size=1920):
    """
    Resizes an image field to a maximum dimension, preserving EXIF.
    Returns a ContentFile if resized, or None if no resize was needed or on error.
    """
    try:
        image_field.open("rb")
        img = Image.open(image_field.file)
        exif_dict = img.info.get("exif")

        # Check if we need to resize
        width, height = img.size
        if width <= max_size and height <= max_size:
            image_field.close()
            return None

        # Calculate new dimensions
        if width > height:
            new_height = int((height * max_size) / width)
            new_width = max_size
        else:
            new_width = int((width * max_size) / height)
            new_height = max_size

        img = img.resize((new_width, new_height), Image.LANCZOS)

        # Save to buffer
        buf = BytesIO()
        if exif_dict:
            img.save(buf, format="JPEG", quality=85, optimize=True, exif=exif_dict)
        else:
            img.save(buf, format="JPEG", quality=85, optimize=True)

        buf.seek(0)
        image_field.close()

        original_name = os.path.basename(image_field.name)
        return ContentFile(buf.read(), name=original_name)

    except Exception as e:
        logger.warning(f"Error resizing original image: {e}")
        try:
            image_field.close()
        except Exception:
            pass
        return None
