# route_optimizer/models/penalties.py
from dataclasses import dataclass

@dataclass
class Penalties:
    Pt: float = 0.0  # Traffic congestion
    Pw: float = 0.0  # Weather condition
    Pter: float = 0.0  # Terrain difficulty
    Pwind: float = 0.0  # Wind speed

    def calculate(self, traffic_data: dict, weather_data: dict, elevation_data: dict) -> None:
        # Traffic Penalty (Pt): Congestion level
        free_flow_duration = traffic_data["distance"] / 100  # Free-flow speed = 100 km/h
        self.Pt = ((traffic_data["duration"] - free_flow_duration) / free_flow_duration 
                  if free_flow_duration and traffic_data["duration"] > free_flow_duration else 0)

        # Weather Penalty (Pw): Based on condition
        condition = weather_data.get("weather", [{}])[0].get("main", "Clear")
        weather_penalty_map = {
            "Sunny": 0.0, "Clear": 0.0, "Partly cloudy": 0.1, "Cloudy": 0.1,
            "Light rain": 0.2, "Rain": 0.3, "Heavy rain": 0.5,
            "Snow": 0.7, "Light snow": 0.4, "Fog": 0.5, "Mist": 0.3
        }
        self.Pw = weather_penalty_map.get(condition, 0.0)

        # Terrain Penalty (Pter): Elevation change per distance
        self.Pter = (elevation_data["elevation_change"] / traffic_data["distance"] 
                    if traffic_data["distance"] else 0)

        # Wind Penalty (Pwind): Normalized wind speed
        wind_speed = weather_data.get("wind", {}).get("speed", 0)
        self.Pwind = wind_speed / 20  # Max wind speed = 20 m/s

    def to_list(self) -> list:
        return [self.Pt, self.Pw, self.Pter, self.Pwind]