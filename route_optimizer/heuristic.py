from models.penalties import Penalties

class Heuristic:
    def __init__(self, weights: dict = None, fuel_efficiency: float = 15, vehicle_type: str = "petrol"):
        
        default_prefs = {'traffic': 50, 'weather': 50, 'elevation': 50, 'air_quality': 50}
        prefs = weights or default_prefs
        total = sum(prefs.values())
        self.weights = {
            "Wt": prefs['traffic'] / total,  # Time weight from traffic preference
            "We": prefs['elevation'] / total,  # Emissions weight from elevation (proxy)
            "Wa": prefs['air_quality'] / total,  # AQI weight from air_quality
            "W1": 0.025, "W2": 0.025, "W3": 0.025, "W4": 0.025  # Penalties unchanged
        }
        self.fuel_efficiency = fuel_efficiency
        self.emission_factor = self.get_emission_factor(vehicle_type)
    def get_emission_factor(self, vehicle_type: str) -> float:
        """
        Returns the emission factor (kg CO2/km) based on vehicle type.
        """
        vehicle_emission_map = {
            "petrol": 0.192, "diesel": 0.225, "hybrid": 0.107,
            "electric": 0.0, "truck": 0.7, "bus": 0.9
        }
        return vehicle_emission_map.get(vehicle_type.lower(), 0.25)  # Default to 0.25 if unknown

    def calculate_score(self, distance: float, speed: float, aqi: float, penalties: Penalties) -> float:
        T = distance / speed if speed > 0 else float("inf")
        E = distance * self.emission_factor / self.fuel_efficiency
        A = aqi / 500
        penalty_sum = sum(self.weights[f"W{i+1}"] * p for i, p in enumerate(penalties.to_list()))
        score = self.weights["Wt"] * T + self.weights["We"] * E + self.weights["Wa"] * A + penalty_sum
        print(f"T: {T}, E: {E}, A: {A}, Penalty: {penalty_sum}, Score: {score}")
        return score

    def heuristic_estimate(self, distance_remaining: float) -> float:
        T_min = distance_remaining / 100  # Best-case speed
        E_min = (distance_remaining * 0.2) / self.fuel_efficiency  # Best-case emissions
        A_min = 0  # Best-case AQI
        return self.weights["Wt"] * T_min + self.weights["We"] * E_min + self.weights["Wa"] * A_min

        return self.weights["Wt"] * T_min + self.weights["We"] * E_min
