# TASK: Weather Report (On Demand)
# SCHEDULE: on demand
# ENABLED: false
# DESCRIPTION: Sends today's weather to Telegram using open-meteo.com (no API key needed)

import requests
import config

# Set your location in .env as WEATHER_LOCATION (city name or lat,lon).
# Example: WEATHER_LOCATION=South Haven, Michigan USA
# Leave unset to use DEFAULT_LATITUDE / DEFAULT_LONGITUDE below.
LOCATION = config.WEATHER_LOCATION

# Default coordinates used when LOCATION is blank — edit to match your location.
DEFAULT_LATITUDE  = 51.5074   # London
DEFAULT_LONGITUDE = -0.1278

# WMO weather interpretation codes used by open-meteo
WMO_CODES = {
    0:  "Clear sky",
    1:  "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain",  63: "Moderate rain",    65: "Heavy rain",
    71: "Slight snow",  73: "Moderate snow",    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def run():
    lat, lon, location_name = _resolve_location()
    if lat is None:
        _send("Weather unavailable: could not resolve location.")
        return

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":           lat,
                "longitude":          lon,
                "current":            "temperature_2m,weathercode,windspeed_10m,precipitation",
                "temperature_unit":   "celsius",
                "windspeed_unit":     "kmh",
                "precipitation_unit": "mm",
                "timezone":           "auto",
            },
            timeout=10,
        )
        resp.raise_for_status()
        current   = resp.json()["current"]
        temp      = current["temperature_2m"]
        code      = current["weathercode"]
        wind      = current["windspeed_10m"]
        precip    = current["precipitation"]
        condition = WMO_CODES.get(code, f"Condition code {code}")

        message = (
            f"Weather — {location_name}\n"
            f"{condition}\n"
            f"Temperature: {temp}°C\n"
            f"Wind: {wind} km/h\n"
            f"Precipitation: {precip} mm"
        )
        _send(message)
    except Exception as e:
        _send(f"Weather unavailable: {e}")


def _resolve_location():
    """Return (latitude, longitude, display_name) for the configured location."""
    loc = LOCATION.strip()

    # Explicit coordinates: "51.5074,-0.1278"
    if loc and "," in loc:
        try:
            lat_s, lon_s = loc.split(",", 1)
            return float(lat_s.strip()), float(lon_s.strip()), loc
        except ValueError:
            pass

    # City name — geocode via open-meteo's free geocoding API
    if loc:
        try:
            resp = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": loc, "count": 1},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                r    = results[0]
                name = f"{r['name']}, {r.get('admin1', '')} {r.get('country', '')}".strip(", ")
                return r["latitude"], r["longitude"], name
        except Exception as e:
            print(f"[weather] Geocoding error: {e}")
        return None, None, None

    # Fall back to default coordinates
    return DEFAULT_LATITUDE, DEFAULT_LONGITUDE, f"{DEFAULT_LATITUDE}, {DEFAULT_LONGITUDE}"


def _send(text):
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:4000]},
            timeout=10,
        )
