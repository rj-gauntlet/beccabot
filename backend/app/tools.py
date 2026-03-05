"""BeccaBot tools: weather, directions."""

import urllib.parse

import requests

from app.config import (
    HOUSING_ADDRESS,
    OFFICE_ADDRESS,
    OPENWEATHERMAP_API_KEY,
)

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


def get_weather(location: str) -> str:
    """Get current weather for a city/address. Uses OpenWeatherMap."""
    city = LOCATION_ALIASES.get(location.lower().strip(), location)
    # Extract city name for API (Austin, TX -> Austin)
    if "," in city:
        city = city.split(",")[0].strip()

    if not OPENWEATHERMAP_API_KEY:
        return "Weather lookup isn't set up yet. Add OPENWEATHERMAP_API_KEY to .env—or just step outside, I hear that works too."

    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": OPENWEATHERMAP_API_KEY, "units": "imperial"},
            timeout=5,
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
