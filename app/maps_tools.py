# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Maps Platform tools: Geocoding API and Places API (New)."""

import os
from typing import Any, Dict, List
from dotenv import load_dotenv
import requests

load_dotenv()


def _get_api_key() -> str:
    """Retrieve the Google Maps API key from the environment."""
    return os.getenv("GOOGLE_MAPS_API_KEY", "").strip()


def geocode_address(address: str) -> Dict[str, Any]:
    """Turn an address or location name into geographic coordinates (latitude and longitude) using Google Geocoding API.

    Args:
        address: The street address, city, landmark, or location query to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary with the location's name, formatted address, and coordinates (latitude, longitude).
    """
    api_key = _get_api_key()
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {
            "status": "error",
            "message": "GOOGLE_MAPS_API_KEY is not configured. Please set a valid key in .env.",
        }

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        resp = requests.get(url, params={"address": address.strip(), "key": api_key}, timeout=8)
        data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            return {
                "status": "not_found",
                "message": f"Could not geocode address '{address}'. Status: {data.get('status')}",
            }

        first_result = data["results"][0]
        loc = first_result.get("geometry", {}).get("location", {})

        return {
            "status": "success",
            "name": first_result.get("formatted_address", address),
            "address": first_result.get("formatted_address"),
            "location": {
                "latitude": loc.get("lat"),
                "longitude": loc.get("lng"),
            },
        }
    except Exception as e:
        return {"status": "error", "message": f"Geocoding request failed: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str,
    radius_meters: float = 1000.0,
) -> Dict[str, Any]:
    """Find nearby places of a given type around a coordinate using Google Places API (New).

    Args:
        latitude: Latitude coordinate of the search center.
        longitude: Longitude coordinate of the search center.
        place_type: Type of place to search for (e.g. 'restaurant', 'cafe', 'book_store', 'park').
        radius_meters: Radius in meters around the coordinates to search (default 1000.0, max 50000.0).

    Returns:
        A dictionary containing a list of nearby places with key fields (name, address, location).
    """
    api_key = _get_api_key()
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {
            "status": "error",
            "message": "GOOGLE_MAPS_API_KEY is not configured. Please set a valid key in .env.",
        }

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }

    payload = {
        "includedTypes": [place_type.strip().lower()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                },
                "radius": float(radius_meters),
            }
        },
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=8)
        if resp.status_code != 200:
            return {
                "status": "error",
                "message": f"Places API returned HTTP {resp.status_code}: {resp.text}",
            }

        data = resp.json()
        places_raw = data.get("places", [])
        results: List[Dict[str, Any]] = []

        for p in places_raw:
            disp_name = (p.get("displayName") or {}).get("text", "")
            addr = p.get("formattedAddress", "")
            loc = p.get("location", {})
            results.append({
                "name": disp_name,
                "address": addr,
                "location": {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                },
            })

        return {
            "status": "success",
            "place_type": place_type,
            "count": len(results),
            "places": results,
        }
    except Exception as e:
        return {"status": "error", "message": f"Places search request failed: {str(e)}"}
