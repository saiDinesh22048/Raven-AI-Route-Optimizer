# route_optimizer/api_clients/google_maps.py
import requests
from dotenv import load_dotenv
import os
from typing import List, Dict, Tuple  # Updated import

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class GoogleMapsClient:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.directions_url = "https://maps.googleapis.com/maps/api/directions/json"
        self.geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"

    def get_directions(self, origin: str, destination: str, alternatives: bool = False) -> List[Dict]:
        """
        Fetches detailed route data with alternatives between origin and destination.
        Args:
            origin: String with lat,lon or place name (e.g., "15.9899142,74.50661989999999").
            destination: String with lat,lon or place name (e.g., "Mumbai").
            alternatives: Boolean to request alternative routes (default: False).
        Returns:
            List of route dictionaries from the Google Maps Directions API response.
        """
        params = {
            "origin": origin,
            "destination": destination,
            "key": self.api_key
        }
        if alternatives:
            params["alternatives"] = "true"
        try:
            response = requests.get(self.directions_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK":
                return data.get("routes", [])
            else:
                raise ValueError(f"Google Maps API error: {data.get('status')} - {data.get('error_message', 'No error message')}")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error during directions request: {str(e)}")
        except ValueError as e:
            raise ValueError(f"Failed to parse directions response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error during directions request: {str(e)}")

    def get_traffic_data(self, origin: str, destination: str) -> dict:
        """
        Fetches traffic data between origin and destination.
        Args:
            origin: String with lat,lon or place name (e.g., "40.7128,-74.0060" or "New York, NY").
            destination: String with lat,lon or place name.
        Returns:
            Dict with distance (km), duration (hours), and speed (km/h).
        """
        params = {
            "origin": origin,
            "destination": destination,
            "departure_time": "now",
            "key": self.api_key
        }
        response = requests.get(self.directions_url, params=params)
        data = response.json()
        if "routes" in data and data["routes"]:
            leg = data["routes"][0]["legs"][0]
            distance = leg["distance"]["value"] / 1000
            duration = leg["duration_in_traffic"]["value"] / 3600
            speed = distance / duration if duration > 0 else 0
            return {"distance": distance, "duration": duration, "speed": speed}
        return {"distance": 0, "duration": 0, "speed": 0}

    def geocode(self, address: str) -> List[Tuple[float, float]]:
        """
        Converts a place name or address to geographic coordinates.
        Args:
            address: String with place name or address (e.g., "Udumalpet").
        Returns:
            List of (latitude, longitude) tuples; typically returns the first result.
        """
        params = {
            "address": address,
            "key": self.api_key
        }
        response = requests.get(self.geocode_url, params=params)
        data = response.json()
        if data.get("status") == "OK" and data.get("results"):
            results = data["results"]
            return [(result["geometry"]["location"]["lat"], result["geometry"]["location"]["lng"]) for result in results]
        return []