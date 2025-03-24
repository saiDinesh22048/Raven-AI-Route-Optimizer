import requests
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleElevationClient:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        self.base_url = "https://maps.googleapis.com/maps/api/elevation/json"

    def get_elevation(self, start: tuple, end: tuple) -> dict:
        """
        Fetches elevation data for start and end points.
        """
        locations = f"{start[0]},{start[1]}|{end[0]},{end[1]}"
        params = {
            "locations": locations,
            "key": self.api_key
        }
        logger.info(f"Fetching elevation for locations: {locations}")
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            logger.info(f"Elevation API response: {data}")

            if data.get("status") == "OK" and "results" in data and len(data["results"]) == 2:
                elevation_change = abs(data["results"][1]["elevation"] - data["results"][0]["elevation"])
                logger.info(f"Elevation change calculated: {elevation_change} meters")
                return {"elevation_change": elevation_change}
            else:
                logger.error(f"Elevation API failed: {data.get('status', 'Unknown error')}")
                return {"elevation_change": 0}

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {"elevation_change": 0}
        except ValueError as e:
            logger.error(f"Json decode error: {e}")
            return {"elevation_change": 0}