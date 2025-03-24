# route_optimizer/api_clients/weatherapi.py
import requests
from dotenv import load_dotenv
import os

load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")  # Add this to your .env

class WeatherAPIClient:
    def __init__(self):
        self.api_key = WEATHER_API_KEY
        self.base_url = "http://api.weatherapi.com/v1/current.json"

    def get_weather(self, lat: float, lon: float) -> dict:
        """
        Fetches current weather data for a given latitude and longitude using WeatherAPI.com.
        Args:
            lat: Latitude of the location (e.g., 40.7128).
            lon: Longitude of the location (e.g., -74.0060).
        Returns:
            Dict with weather condition and wind speed, compatible with penalties.py.
        """
        params = {
            "key": self.api_key,
            "q": f"{lat},{lon}"  # WeatherAPI uses "lat,lon" format for queries
        }
        response = requests.get(self.base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            condition = data["current"]["condition"]["text"]  # e.g., "Sunny", "Light rain"
            wind_speed = data["current"]["wind_kph"] / 3.6  # Convert km/h to m/s
            return {
                "weather": [{"main": condition}],  # Mimics OpenWeatherMap structure
                "wind": {"speed": wind_speed}
            }
        return {}