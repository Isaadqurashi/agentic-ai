from __future__ import annotations

from typing import Any

import httpx


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(latitude: float, longitude: float) -> dict[str, Any]:
    if not -90 <= float(latitude) <= 90:
        raise ValueError("latitude must be between -90 and 90")
    if not -180 <= float(longitude) <= 180:
        raise ValueError("longitude must be between -180 and 180")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "timezone": "auto",
    }
    with httpx.Client(timeout=10) as client:
        response = client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
    return response.json()


def _build_server() -> Any:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("weather_server")
    mcp.tool()(get_weather)
    return mcp


def main() -> None:
    _build_server().run()


if __name__ == "__main__":
    main()
