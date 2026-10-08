import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10.0


def weather_tool(state):
    print("\n===== WEATHER TOOL =====")

    location = state["tool_input"].strip()

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            geocoding_response = client.get(
                GEOCODING_URL,
                params={
                    "name": location,
                    "count": 1,
                    "language": "en",
                    "format": "json",
                },
            )
            geocoding_response.raise_for_status()
            geocoding_data = geocoding_response.json()

            results = geocoding_data.get("results", [])

            if not results:
                return {
                    "messages": [],
                    "output": {},
                    "success": False,
                    "error": f"Location not found: {location}",
                }

            place = results[0]

            forecast_response = client.get(
                FORECAST_URL,
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": (
                        "temperature_2m,"
                        "weather_code,"
                        "precipitation,"
                        "rain"
                    ),
                    "hourly": (
                        "precipitation_probability,"
                        "precipitation,"
                        "rain,"
                        "temperature_2m,"
                        "weather_code"
                    ),
                    "forecast_days": 1,
                    "timezone": "auto",
                },
            )
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()

        current = forecast_data.get("current", {})
        hourly = forecast_data.get("hourly", {})
        probabilities = hourly.get(
            "precipitation_probability",
            [],
        )

        output = {
            "location": place.get("name", location),
            "country": place.get("country"),
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "timezone": forecast_data.get("timezone"),
            "current": current,
            "today": {
                "max_precipitation_probability": (
                    max(probabilities)
                    if probabilities
                    else None
                ),
                "hourly_precipitation_probability": probabilities,
                "hourly_time": hourly.get("time", []),
            },
        }

        return {
            "messages": [],
            "output": output,
            "success": True,
            "error": None,
        }

    except (httpx.HTTPError, ValueError, KeyError) as exc:
        return {
            "messages": [],
            "output": {},
            "success": False,
            "error": str(exc),
        }
