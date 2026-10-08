from unittest.mock import Mock, patch

from tools.weather import weather_tool


def test_weather_tool_success():

    geocoding_response = Mock()
    geocoding_response.raise_for_status.return_value = None
    geocoding_response.json.return_value = {
        "results": [
            {
                "name": "Mumbai",
                "country": "India",
                "latitude": 19.07283,
                "longitude": 72.88261,
            }
        ]
    }

    forecast_response = Mock()
    forecast_response.raise_for_status.return_value = None
    forecast_response.json.return_value = {
        "timezone": "Asia/Kolkata",
        "current": {
            "time": "2026-10-06T12:00",
            "temperature_2m": 33.2,
            "weather_code": 0,
            "precipitation": 0.0,
            "rain": 0.0,
        },
        "hourly": {
            "time": [
                "2026-10-06T12:00",
                "2026-10-06T13:00",
                "2026-10-06T14:00",
            ],
            "precipitation_probability": [
                12,
                30,
                56,
            ],
        },
    }

    with patch("tools.weather.httpx.Client") as mock_client:

        client = mock_client.return_value.__enter__.return_value

        client.get.side_effect = [
            geocoding_response,
            forecast_response,
        ]

        result = weather_tool(
            {"tool_input": "Mumbai, India"}
        )

    assert result["success"] is True
    assert result["error"] is None

    assert result["output"]["location"] == "Mumbai"
    assert result["output"]["country"] == "India"
    assert result["output"]["latitude"] == 19.07283
    assert result["output"]["longitude"] == 72.88261

    assert (
        result["output"]["today"]["max_precipitation_probability"]
        == 56
    )

    assert client.get.call_count == 2


def test_weather_tool_location_not_found():

    geocoding_response = Mock()
    geocoding_response.raise_for_status.return_value = None
    geocoding_response.json.return_value = {
        "results": []
    }

    with patch("tools.weather.httpx.Client") as mock_client:

        client = mock_client.return_value.__enter__.return_value

        client.get.return_value = geocoding_response

        result = weather_tool(
            {"tool_input": "UnknownPlaceXYZ"}
        )

    assert result["success"] is False
    assert result["output"] == {}
    assert "Location not found" in result["error"]

    assert client.get.call_count == 1