from typing import List, Dict, Tuple, Set
import heapq
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from api_clients.google_maps import GoogleMapsClient
from api_clients.google_airquality import GoogleAirQualityClient
from api_clients.weatherapi import WeatherAPIClient
from api_clients.google_elevation import GoogleElevationClient
from models.penalties import Penalties
from heuristic import Heuristic
import time
import threading
import math  # Added for Haversine formula

class RouteGraph:
    def __init__(self):
        self.gmaps = GoogleMapsClient()
        self.air_quality = GoogleAirQualityClient()
        self.weather = WeatherAPIClient()
        self.elevation = GoogleElevationClient()
        self.heuristic = Heuristic()
        self.api_key = "AIzaSyBvMuJWIj6jEaIUgHoNdGZHZkkHEWvE9QI"  # Move to config/env in production
        self.current_route = None
        self.step_index = 0
        self.MIN_DISTANCE_THRESHOLD = 0.5  # 500 meters in kilometers

    def haversine_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """
        Calculate the distance between two points on Earth using the Haversine formula.
        Args:
            coord1: Tuple of (latitude, longitude) for the first point.
            coord2: Tuple of (latitude, longitude) for the second point.
        Returns:
            Distance in kilometers.
        """
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        # Radius of the Earth in kilometers
        R = 6371.0

        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Differences in coordinates
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine formula
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance

    def find_optimal_route(self, source: str, destination: str, preferences: dict = None) -> List[str]:
        """Calculate initial optimal route with coordinates."""
        routes = self.generate_all_routes(source, destination)
        print(f"Total Routes Found: {len(routes)}")
        
        graphs = []
        for i, route in enumerate(routes):
            heuristic_values = self.calculate_heuristic_values(route, preferences)
            graph = self.construct_graph(route, heuristic_values)
            graphs.append(graph)
            print(f"Route {i+1}: {len(route)-2} Intermediate Nodes")
            print(f"Graph {i+1}: {graph}\n")
        
        merged_graph = self.merge_graphs(graphs)
        print("Merged Graph:")
        for start, edges in merged_graph.items():
            for end, weight in edges.items():
                print(f"{start} -> {end}: {weight}")
        
        optimal_route = self.apply_a_star(merged_graph, source, destination)
        optimal_route_coords = [self.get_coordinates_str(node) for node in optimal_route]
        print("\nOptimal Route (coords):", optimal_route_coords)
        
        return optimal_route_coords

    def dynamic_route_optimization(self, source: str, destination: str, 
                                 update_interval: float = 1.0,
                                 preferences: dict = None,
                                 route_data: dict = None,
                                 marker_close_event=None) -> Dict:
        if route_data is None:
            route_data = {"status": "idle", "final_route": [], "alternative_routes": []}
        print(f"Starting from: {source} to: {destination} with preferences: {preferences}")
        
        source_coords = self.get_coordinates_str(source)
        dest_coords = self.get_coordinates_str(destination)
        
        self.current_route = self.find_optimal_route(source_coords, dest_coords, preferences)
        route_data["status"] = "running"
        route_data["final_route"] = [source_coords]
        route_data["alternative_routes"] = []  # Initialize as a list of dictionaries
        self.step_index = 0

        while self.step_index < len(self.current_route) - 1:
            current_node = self.current_route[self.step_index]
            next_node = self.current_route[self.step_index + 1]
            
            if next_node not in route_data["final_route"]:
                route_data["final_route"].append(next_node)
                print(f"DEBUG: Updated final_route: {route_data['final_route']}")
                
                # Wait for marker to get close to next_node
                if marker_close_event:
                    print(f"Waiting for marker to reach {next_node}")
                    marker_close_event.wait()
                    marker_close_event.clear()
            
            # Check for alternatives, log them, and store them
            alternative_routes = self.generate_all_routes(next_node, dest_coords)
            num_alternatives = len(alternative_routes)
            print(f"\nAt subnode {next_node}: {num_alternatives} alternative routes available")
            
            # Log each alternative route
            for i, alt_route in enumerate(alternative_routes, 1):
                print(f"Alternative Route {i}: {alt_route}")
            
            # Store alternatives in route_data as a dictionary
            route_data["alternative_routes"].append({
                "node": next_node,
                "alternatives": alternative_routes
            })
            
            if num_alternatives > 1:
                print(f"Multiple routes detected from {next_node}, recalculating...")
                graphs = []
                for i, route in enumerate(alternative_routes):
                    heuristic_values = self.calculate_heuristic_values(route, preferences)
                    graph = self.construct_graph(route, heuristic_values)
                    graphs.append(graph)
                
                merged_graph = self.merge_graphs(graphs)
                new_optimal_route = self.apply_a_star(merged_graph, next_node, dest_coords)
                new_optimal_route_coords = [self.get_coordinates_str(node) for node in new_optimal_route]
                print(f"New Optimal Route from {next_node}: {new_optimal_route_coords}")
                self.current_route = route_data["final_route"][:-1] + new_optimal_route_coords
                self.step_index = len(route_data["final_route"]) - 2
            
            if next_node == dest_coords:
                print("Destination reached!")
                route_data["status"] = "completed"
                break
                
            self.step_index += 1
            time.sleep(update_interval)
        
        print("\nFinal Route Taken:", route_data["final_route"])
        print("\nStored Alternative Routes:")
        for alt in route_data["alternative_routes"]:
            print(f"From node {alt['node']}:")
            for i, alt_route in enumerate(alt['alternatives'], 1):
                print(f"  Alternative Route {i}: {alt_route}")
        return route_data

    def generate_all_routes(self, source: str, destination: str) -> List[List[str]]:
        routes_data = self.gmaps.get_directions(source, destination, alternatives=True)
        routes = []
        for route in routes_data:
            steps = route["legs"][0]["steps"]
            route_stations = [source]
            last_coords = self.get_coordinates(source)

            for step in steps:
                end_location = step["end_location"]
                station = f"{end_location['lat']},{end_location['lng']}"
                current_coords = (end_location['lat'], end_location['lng'])

                # Calculate distance from the last node
                distance = self.haversine_distance(last_coords, current_coords)
                print(f"Distance from {route_stations[-1]} to {station}: {distance:.3f} km")  # Debug log

                # Only add the node if it's farther than 500 meters from the last node
                if distance >= self.MIN_DISTANCE_THRESHOLD:
                    route_stations.append(station)
                    last_coords = current_coords
                else:
                    print(f"Skipping node {station} (distance {distance:.3f} km < {self.MIN_DISTANCE_THRESHOLD} km)")

            # Ensure the destination is always included, even if it's close to the last node
            if route_stations[-1] != destination:
                route_stations[-1] = destination
            routes.append(route_stations)
        return routes

    def calculate_heuristic_values(self, route: List[str], preferences: dict = None) -> Dict[Tuple[str, str], float]:
        heuristic_values = {}
        segments = [(route[i], route[i + 1]) for i in range(len(route) - 1)]

        def fetch_segment_data(segment):
            start, end = segment
            start_coords = self.get_coordinates(start)
            end_coords = self.get_coordinates(end)
            traffic_data = self.gmaps.get_traffic_data(start, end)
            weather_data = self.weather.get_weather(*start_coords)
            elevation_data = self.elevation.get_elevation(start_coords, end_coords)
            aqi = self.air_quality.get_aqi(*start_coords)
            return (start, end), (traffic_data, weather_data, elevation_data, aqi)

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(fetch_segment_data, segments))

        for (start, end), (traffic_data, weather_data, elevation_data, aqi) in results:
            penalties = Penalties()
            penalties.calculate(traffic_data, weather_data, elevation_data)
            traffic_weight = preferences.get('traffic', 50) / 100.0 if preferences else 0.5
            weather_weight = preferences.get('weather', 50) / 100.0 if preferences else 0.5
            elevation_weight = preferences.get('elevation', 50) / 100.0 if preferences else 0.5
            aqi_weight = preferences.get('air_quality', 50) / 100.0 if preferences else 0.5
            score = self.heuristic.calculate_score(
                traffic_data["distance"], traffic_data["speed"], aqi, penalties
            ) * (traffic_weight + weather_weight + elevation_weight + aqi_weight) / 4
            heuristic_values[(start, end)] = score
        return heuristic_values

    def get_coordinates(self, location: str) -> Tuple[float, float]:
        if self.is_lat_lon(location):
            return tuple(map(float, location.split(",")))
        return self.gmaps.geocode(location)[0]

    def get_coordinates_str(self, location: str) -> str:
        lat, lng = self.get_coordinates(location)
        return f"{lat},{lng}"

    def is_lat_lon(self, location: str) -> bool:
        try:
            parts = location.split(",")
            if len(parts) != 2:
                return False
            float(parts[0])
            float(parts[1])
            return True
        except ValueError:
            return False

    def construct_graph(self, route: List[str], heuristic_values: Dict[Tuple[str, str], float]) -> Dict[str, Dict[str, float]]:
        graph = defaultdict(dict)
        for i in range(len(route) - 1):
            start, end = route[i], route[i + 1]
            graph[start][end] = heuristic_values[(start, end)]
        return dict(graph)

    def merge_graphs(self, graphs: List[Dict[str, Dict[str, float]]]) -> Dict[str, Dict[str, float]]:
        merged = defaultdict(dict)
        for graph in graphs:
            for start, neighbors in graph.items():
                for end, weight in neighbors.items():
                    if end in merged[start]:
                        merged[start][end] = min(merged[start][end], weight)
                    else:
                        merged[start][end] = weight
        return dict(merged)

    def apply_a_star(self, graph: Dict[str, Dict[str, float]], start: str, goal: str) -> List[str]:
        open_set = [(0, start, [start])]
        heapq.heapify(open_set)
        closed_set: Set[str] = set()
        g_score = {start: 0}
        f_score = {start: self.heuristic.heuristic_estimate(self.get_distance(start, goal))}

        while open_set:
            _, current, path = heapq.heappop(open_set)
            if current == goal:
                return path
            if current in closed_set:
                continue
            closed_set.add(current)
            for neighbor, weight in graph.get(current, {}).items():
                tentative_g_score = g_score[current] + weight
                if neighbor in closed_set and tentative_g_score >= g_score.get(neighbor, float("inf")):
                    continue
                if tentative_g_score < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = tentative_g_score
                    distance_to_goal = self.get_distance(neighbor, goal)
                    f_score[neighbor] = g_score[neighbor] + self.heuristic.heuristic_estimate(distance_to_goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor, path + [neighbor]))
        return []

    def get_distance(self, start: str, end: str) -> float:
        traffic_data = self.gmaps.get_traffic_data(start, end)
        return traffic_data["distance"]

if __name__ == "__main__":
    route_graph = RouteGraph()
    source = "Dharapuram"
    destination = "Udumalpet"
    route_data = {"status": "idle", "final_route": [], "alternative_routes": []}
    final_route = route_graph.dynamic_route_optimization(
        source, destination, 
        update_interval=5.0, 
        preferences={'traffic': 50, 'weather': 70}, 
        route_data=route_data
    )
    print(f"Final Route Data: {route_data}")