"""BeccaBot tools: weather, directions, current time."""

import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

# City/place -> IANA timezone
TIMEZONE_ALIASES = {
    "austin": "America/Chicago",
    "housing": "America/Chicago",
    "placemakr": "America/Chicago",
    "office": "America/Chicago",
    "new york": "America/New_York",
    "la": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "london": "Europe/London",
    "utc": "UTC",
}

from app.config import (
    HOUSING_ADDRESS,
    OFFICE_ADDRESS,
    OPENWEATHERMAP_API_KEY,
)

# Open-Meteo WMO weather codes (simplified)
_WEATHER_DESCRIPTIONS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    77: "snow grains",
    80: "slight rain showers",
    81: "rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}

LOCATION_ALIASES = {
    "housing": HOUSING_ADDRESS,
    "placemakr": HOUSING_ADDRESS,
    "place maker": HOUSING_ADDRESS,
    "place makr": HOUSING_ADDRESS,
    "office": OFFICE_ADDRESS,
    "the office": OFFICE_ADDRESS,
    "hq": OFFICE_ADDRESS,
    "headquarters": OFFICE_ADDRESS,
    "gauntlet": OFFICE_ADDRESS,
    "austin": "Austin, TX",
}


def _get_weather_open_meteo(location: str) -> str:
    """Get weather via Open-Meteo (no API key required)."""
    city = LOCATION_ALIASES.get(location.lower().strip(), location)
    if "," in city:
        city = city.split(",")[0].strip()

    headers = {"User-Agent": "BeccaBot/1.0 (Gauntlet AI assistant)"}
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            headers=headers,
            timeout=10,
        )
        geo.raise_for_status()
        data = geo.json()
        results = data.get("results") or []
        if not results:
            return f"Couldn't find a place named '{city}'."
        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        name = results[0].get("name", city)

        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code",
                "temperature_unit": "fahrenheit",
            },
            headers=headers,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        cur = data.get("current") or {}
        temp = cur.get("temperature_2m")
        humidity = cur.get("relative_humidity_2m", "N/A")
        code = cur.get("weather_code", 0)
        desc = _WEATHER_DESCRIPTIONS.get(code, "unknown conditions")
        if temp is not None:
            return f"{name}: {temp}°F, {desc}. Humidity {humidity}%."
        return "Couldn't get current weather. Try again?"
    except requests.RequestException as e:
        return f"Couldn't fetch weather: {e}"
    except (KeyError, IndexError, TypeError):
        return "Got weird data from the weather service. Try again?"


def get_weather(location: str) -> str:
    """Get current weather for a city/address. Uses OpenWeatherMap if key set, else Open-Meteo."""
    city = LOCATION_ALIASES.get(location.lower().strip(), location)
    if "," in city:
        city = city.split(",")[0].strip()

    if OPENWEATHERMAP_API_KEY:
        headers = {"User-Agent": "BeccaBot/1.0 (Gauntlet AI assistant)"}
        try:
            r = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": OPENWEATHERMAP_API_KEY, "units": "imperial"},
                headers=headers,
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            humidity = data["main"].get("humidity", "N/A")
            return f"{city}: {temp}°F, {desc}. Humidity {humidity}%."
        except requests.RequestException as e:
            return f"Couldn't fetch weather: {e}"
        except (KeyError, IndexError):
            return "Got weird data from the weather service. Try again?"

    return _get_weather_open_meteo(location)


def _resolve_location(loc: str) -> str:
    """Resolve 'housing', 'office', or any address/place in Austin to a Google Maps–friendly string."""
    if not loc or not loc.strip():
        return "Austin, TX"
    key = loc.lower().strip()
    if key in LOCATION_ALIASES:
        return LOCATION_ALIASES[key]
    # Free-form address or place; append Austin if it doesn't already include it
    if "austin" not in key and "tx" not in key:
        return f"{loc.strip()}, Austin, TX"
    return loc.strip()


def get_current_time(location: str = "Austin") -> str:
    """Get the current date and time for a city/timezone. Use America/Chicago for Austin."""
    key = location.strip().lower() if location else "austin"
    tz_name = TIMEZONE_ALIASES.get(key, "America/Chicago")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("America/Chicago")
    now = datetime.now(tz)
    return now.strftime("%A, %B %d at %I:%M %p %Z")


def get_directions(origin: str, destination: str, travel_mode: str = "driving") -> str:
    """Get a Google Maps directions link. Supports housing, office, or any address/place in Austin."""
    o = _resolve_location(origin)
    d = _resolve_location(destination)
    base = "https://www.google.com/maps/dir/"
    params = urllib.parse.urlencode(
        {"api": "1", "origin": o, "destination": d, "travelmode": travel_mode}
    )
    url = f"{base}?{params}"
    return url
