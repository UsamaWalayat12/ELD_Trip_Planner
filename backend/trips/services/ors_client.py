"""
Phase 3 — OpenRouteService API Client
Handles geocoding and HGV route calculation.
"""
import requests
from django.conf import settings


ORS_BASE = "https://api.openrouteservice.org"


def _headers():
    return {
        "Authorization": settings.ORS_API_KEY,
        "Content-Type": "application/json",
    }


def geocode(address: str) -> dict:
    """
    Convert a text address to lat/lng using ORS geocode/search.

    Returns:
        {
            "lat": float,
            "lng": float,
            "display_name": str
        }

    Raises:
        ValueError: if no result found or API error.
    """
    url = f"{ORS_BASE}/geocode/search"
    params = {
        "api_key": settings.ORS_API_KEY,
        "text": address,
        "size": 1,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    if not features:
        raise ValueError(f"No geocoding results found for: '{address}'")

    feature = features[0]
    coords = feature["geometry"]["coordinates"]  # [lng, lat]
    display = feature["properties"].get("label", address)

    return {
        "lat": coords[1],
        "lng": coords[0],
        "display_name": display,
    }


def get_route(origin: dict, destination: dict) -> dict:
    """
    Get a driving-hgv route between two points using ORS.

    Args:
        origin: {"lat": float, "lng": float}
        destination: {"lat": float, "lng": float}

    Returns:
        {
            "distance_meters": float,
            "duration_seconds": float,
            "geometry": [[lng, lat], ...]   # list of coordinate pairs
        }

    Raises:
        ValueError: if routing fails.
    """
    url = f"{ORS_BASE}/v2/directions/driving-hgv/geojson"
    payload = {
        "coordinates": [
            [origin["lng"], origin["lat"]],
            [destination["lng"], destination["lat"]],
        ],
        "instructions": False,
    }
    resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    if not features:
        raise ValueError("ORS returned no route features.")

    feature = features[0]
    summary = feature["properties"]["summary"]
    geometry_coords = feature["geometry"]["coordinates"]  # list of [lng, lat]

    return {
        "distance_meters": summary["distance"],
        "duration_seconds": summary["duration"],
        "geometry": geometry_coords,
    }


def get_full_route(points: list) -> dict:
    """
    Get a multi-waypoint route.

    Args:
        points: list of {"lat": float, "lng": float}

    Returns: same shape as get_route()
    """
    url = f"{ORS_BASE}/v2/directions/driving-hgv/geojson"
    payload = {
        "coordinates": [[p["lng"], p["lat"]] for p in points],
        "instructions": False,
    }
    resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    if not features:
        raise ValueError("ORS returned no route features.")

    feature = features[0]
    summary = feature["properties"]["summary"]
    geometry_coords = feature["geometry"]["coordinates"]

    return {
        "distance_meters": summary["distance"],
        "duration_seconds": summary["duration"],
        "geometry": geometry_coords,
    }
