from flask import Flask, request, jsonify, send_from_directory  # Importing flask module in the project is mandatory    
from flask_cors import CORS
from graph import RouteGraph
import threading
import time
from threading import Lock
import os

app = Flask(__name__, static_folder='static')
CORS(app)

class RouteState:
    def __init__(self):
        self.lock = Lock()
        self.route_graph = None
        self.update_thread = None
        self.route_data = {
            "status": "idle",
            "final_route": [],
            "gps_position": None,
            "alternative_routes": []
        }
        self.marker_close_event = threading.Event()

    def reset(self):
        with self.lock:
            if self.update_thread and self.update_thread.is_alive():
                print("Stopping existing optimization thread...")
                self.route_data["status"] = "idle"
                self.marker_close_event.set()
                self.update_thread.join(timeout=2)
            self.route_graph = None
            self.update_thread = None
            self.route_data = {
                "status": "idle",
                "final_route": [],
                "gps_position": None,
                "alternative_routes": []
            }
            self.marker_close_event.clear()
            print("Backend state reset.")

state = RouteState()

@app.route('/')
def home():
    state.reset()
    return app.send_static_file('home.html')

@app.route('/optimize', methods=['POST'])
def optimize_route():
    with state.lock:
        # Check if completed, but ensure final_route has data
        if state.route_data["status"] == "completed":
            if not state.route_data["final_route"]:
                return jsonify({"status": "completed", "message": "No route data available yet"}), 200
            return jsonify({
                "status": "already completed",
                "source": state.route_data["final_route"][0],
                "destination": state.route_data["final_route"][-1]
            }), 200

        # Check if running, but ensure final_route has data
        if state.update_thread and state.update_thread.is_alive():
            if not state.route_data["final_route"]:
                return jsonify({"status": "running", "message": "Optimization in progress, no route yet"}), 200
            return jsonify({
                "status": "already running",
                "source": state.route_data["final_route"][0],
                "destination": "Mangalagiri"
            }), 200

        data = request.get_json()
        if not data or 'source' not in data or 'destination' not in data:
            return jsonify({"error": "Missing required fields: source and destination"}), 400

        source = data['source']
        destination = data['destination']
        preferences = data.get('preferences', {
            'traffic': 50,
            'weather': 70,
            'elevation': 30,
            'air_quality': 80
        })

        try:
            if not state.route_graph:
                state.route_graph = RouteGraph()

            state.route_data["status"] = "running"
            state.route_data["final_route"] = [source]  # Ensure source is set here
            state.marker_close_event.clear()

            state.update_thread = threading.Thread(
                target=run_optimization,
                args=(source, destination, preferences)
            )
            state.update_thread.start()

            return jsonify({
                "status": "started",
                "source": source,
                "destination": destination
            })
        except Exception as e:
            return jsonify({"error": f"Optimization failed: {str(e)}"}), 500

def run_optimization(source, destination, preferences):
    try:
        result = state.route_graph.dynamic_route_optimization(
            source,
            destination,
            update_interval=1.0,
            preferences=preferences,
            route_data=state.route_data,
            marker_close_event=state.marker_close_event
        )
        with state.lock:
            state.route_data["status"] = "completed"
        print("Optimization completed:", state.route_data)
    except Exception as e:
        with state.lock:
            state.route_data["status"] = "error"
            state.route_data["error"] = str(e)
        print(f"Optimization failed: {str(e)}")

@app.route('/status', methods=['GET'])
def get_status():
    with state.lock:
        print("Serving route_data:", state.route_data)
        return jsonify(state.route_data)

@app.route('/marker-close', methods=['POST'])
def marker_close():
    data = request.get_json()
    if not data or "node" not in data:
        return jsonify({"error": "Missing node parameter"}), 400

    print(f"Marker close to {data['node']}")
    state.marker_close_event.set()
    return jsonify({"status": "received"}), 200

@app.route('/reset', methods=['GET'])
def reset_state():
    state.reset()
    return jsonify({"status": "backend reset"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')