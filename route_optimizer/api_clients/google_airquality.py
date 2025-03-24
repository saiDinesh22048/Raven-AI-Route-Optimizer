# route_optimizer/api_clients/google_airquality.py
import requests
from dotenv import load_dotenv
import os

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class GoogleAirQualityClient:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.base_url = "https://airquality.googleapis.com/v1/currentConditions:lookup"

    def get_aqi(self, lat: float, lon: float) -> float:
        """
        Fetches the current AQI for a given latitude and longitude.
        Args:
            lat: Latitude of the location.
            lon: Longitude of the location.
        Returns:
            AQI value (float) or 0 if the request fails.
        """
        headers = {"Content-Type": "application/json"}
        payload = {
            "location": {"latitude": lat, "longitude": lon}
        }
        response = requests.post(self.base_url, json=payload, headers=headers, params={"key": self.api_key})
        data = response.json()
        if "indexes" in data and data["indexes"]:
            return float(data["indexes"][0]["aqi"])
        return 0.0