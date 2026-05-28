import requests
import logging

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
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true"
        }
        
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
