import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import L from "leaflet";
import "leaflet-routing-machine";
import "./styles.css";

function App() {
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const routeControlRef = useRef(null);
  const [routeData, setRouteData] = useState({
    status: "idle",
    final_route: [],
    alternative_routes: [],
  });
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [currentPosition, setCurrentPosition] = useState(null);
  const [source, setSource] = useState("Kuragallu");
  const [destination, setDestination] = useState("Mangalagiri");
  const [isAnimating, setIsAnimating] = useState(false);
  const [currentNodeIndex, setCurrentNodeIndex] = useState(0);
  const [preferences, setPreferences] = useState({
    traffic: 50,
    weather: 50,
    elevation: 50,
    air_quality: 50,
  });
  const [notification, setNotification] = useState(null); // New state for notification

  const CONFIG = {
    API_BASE_URL: "http://localhost:5000",
    POLLING_INTERVAL: 500,
    WAIT_TIME_MS: 3000,
    PROXIMITY_THRESHOLD: 0.01,
  };

  const ALT_ROUTE_COLORS = [
    "#FF00FF",
    "#00CED1",
    "#FFA500",
    "#8A2BE2",
    "#00FF7F",
    "#FF4500",
    "#1E90FF",
    "#FFD700",
  ];

  const getCoordinatesFromPlace = (place) => {
    const coords = {
      Kuragallu: [16.4543715, 80.5250379],
      Mangalagiri: [16.4308, 80.5682],
    };
    return coords[place] || null;
  };

  const getCoordinates = (location) => {
    const [lat, lng] = location.split(",").map(Number);
    if (!isNaN(lat) && !isNaN(lng)) return L.latLng(lat, lng);
    const placeCoords = getCoordinatesFromPlace(location);
    return placeCoords
      ? L.latLng(placeCoords[0], placeCoords[1])
      : L.latLng(16.4308, 80.5682);
  };

  const resetApp = () => {
    if (mapRef.current) {
      if (routeControlRef.current) {
        try {
          mapRef.current.removeControl(routeControlRef.current);
          routeControlRef.current = null;
        } catch (e) {
          console.warn("Failed to remove route control:", e);
        }
      }
      mapRef.current.remove();
      mapRef.current = null;
    }
    if (markerRef.current) {
      markerRef.current = null;
    }
    setRouteData({ status: "idle", final_route: [], alternative_routes: [] });
    setStatus("idle");
    setError(null);
    setCurrentPosition(null);
    setIsAnimating(false);
    setCurrentNodeIndex(0);
    setNotification(null); // Reset notification
  };

  useEffect(() => {
    resetApp();
    axios
      .get(`${CONFIG.API_BASE_URL}/reset`)
      .then((response) =>
        console.log("Backend reset confirmed:", response.data)
      )
      .catch((err) => console.error("Failed to confirm backend reset:", err));
    return () => {
      resetApp();
    };
  }, []);

  const initializeMap = (coords) => {
    if (!mapRef.current) {
      mapRef.current = L.map("map").setView(coords, 11);
      L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png", {
        attribution: "Leaflet © OpenStreetMap contributors",
        maxZoom: 18,
      }).addTo(mapRef.current);

      const taxiIcon = L.icon({
        iconUrl: process.env.PUBLIC_URL + "/nav[1].png",
        iconSize: [50, 50],
      });
      markerRef.current = L.marker(coords, { icon: taxiIcon }).addTo(
        mapRef.current
      );

      setTimeout(() => {
        if (mapRef.current) {
          mapRef.current.invalidateSize();
          console.log("Map initialized and size invalidated");
        }
      }, 100);
    }
  };

  const startOptimization = async () => {
    try {
      const response = await axios.post(`${CONFIG.API_BASE_URL}/optimize`, {
        source,
        destination,
        preferences,
      });
      setStatus(response.data.status);
      setCurrentPosition(
        getCoordinatesFromPlace(source) || [16.4543715, 80.5250379]
      );
      setCurrentNodeIndex(0);
    } catch (error) {
      setError(`Error starting optimization: ${error.message}`);
      setStatus("error");
    }
  };

  useEffect(() => {
    let isMounted = true;
    const pollStatus = async () => {
      try {
        const response = await axios.get(`${CONFIG.API_BASE_URL}/status`);
        if (!isMounted) return;

        setRouteData(response.data);
        setStatus(response.data.status);

        if (
          response.data.status === "running" &&
          response.data.final_route.length > currentNodeIndex + 1 &&
          !isAnimating
        ) {
          const startNode = response.data.final_route[currentNodeIndex];
          const nextNode = response.data.final_route[currentNodeIndex + 1];
          console.log(`Polling detected new node: ${startNode} -> ${nextNode}`);
          setIsAnimating(true);
          await updateRoute(
            startNode,
            nextNode,
            response.data.final_route,
            response.data.alternative_routes
          );
          setCurrentNodeIndex((prev) => prev + 1);
          setIsAnimating(false);
        }

        if (response.data.status === "completed" && !isAnimating) {
          console.log("Showing final route");
          showFinalRoute(
            response.data.final_route,
            response.data.alternative_routes
          );
        }
      } catch (error) {
        if (isMounted) setError(`Error polling status: ${error.message}`);
      }
    };

    const intervalId = setInterval(pollStatus, CONFIG.POLLING_INTERVAL);
    if (routeData.status === "completed" || error) clearInterval(intervalId);
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [
    routeData.status,
    routeData.final_route.length,
    error,
    isAnimating,
    currentNodeIndex,
  ]);

  const updateRoute = async (startNode, nextNode, fullRoute, altRoutes) => {
    const startLatLng = getCoordinates(startNode);
    const nextLatLng = getCoordinates(nextNode);

    if (routeControlRef.current && mapRef.current) {
      try {
        mapRef.current.removeControl(routeControlRef.current);
        routeControlRef.current = null;
      } catch (e) {
        console.warn("Failed to remove previous route control:", e);
      }
    }

    if (!mapRef.current) {
      console.error("Map not initialized");
      return;
    }

    const newRouteControl = L.Routing.control({
      waypoints: [startLatLng, nextLatLng],
      lineOptions: { styles: [{ color: "#00FF00", opacity: 1, weight: 4 }] },
      addWaypoints: true,
      routeWhileDragging: false,
      show: true,
    }).addTo(mapRef.current);
    routeControlRef.current = newRouteControl;

    altRoutes.forEach((alt, altIndex) => {
      if (alt.node === startNode && alt.alternatives.length > 1) {
        alt.alternatives.slice(1).forEach((altRoute, i) => {
          const color = ALT_ROUTE_COLORS[i % ALT_ROUTE_COLORS.length];
          const altWaypoints = altRoute.map(getCoordinates);
          L.Routing.control({
            waypoints: altWaypoints,
            lineOptions: { styles: [{ color, opacity: 0.7, weight: 2 }] },
            addWaypoints: false,
            routeWhileDragging: false,
            show: false,
          }).addTo(mapRef.current);
        });
      }
    });

    return new Promise((resolve) => {
      newRouteControl.on("routesfound", (e) => {
        const routeCoordinates = e.routes[0]?.coordinates || [
          { lat: startLatLng.lat, lng: startLatLng.lng },
          { lat: nextLatLng.lat, lng: nextLatLng.lng },
        ];
        console.log("Route coordinates:", routeCoordinates);
        animateMarker(markerRef.current, routeCoordinates, nextLatLng).then(
          resolve
        );
      });

      newRouteControl.on("routingerror", (e) => {
        console.error("Routing error:", e.error);
        setError(`Routing failed: ${e.error.message}`);
        resolve();
      });
    });
  };

  const showFinalRoute = (finalRoute, altRoutes) => {
    if (routeControlRef.current && mapRef.current) {
      try {
        mapRef.current.removeControl(routeControlRef.current);
        routeControlRef.current = null;
      } catch (e) {
        console.warn("Failed to remove final route control:", e);
      }
    }

    if (!mapRef.current) return;

    const waypoints = finalRoute.map(getCoordinates);
    routeControlRef.current = L.Routing.control({
      waypoints,
      lineOptions: { styles: [{ color: "#FF0000", opacity: 1, weight: 4 }] },
      addWaypoints: false,
      routeWhileDragging: false,
      show: true,
    }).addTo(mapRef.current);

    altRoutes.forEach((alt, altIndex) => {
      alt.alternatives.slice(1).forEach((altRoute, i) => {
        const color = ALT_ROUTE_COLORS[i % ALT_ROUTE_COLORS.length];
        const altWaypoints = altRoute.map(getCoordinates);
        L.Routing.control({
          waypoints: altWaypoints,
          lineOptions: { styles: [{ color, opacity: 0.7, weight: 2 }] },
          addWaypoints: false,
          routeWhileDragging: false,
          show: true,
        }).addTo(mapRef.current);
      });
    });
  };

  const animateMarker = (marker, coordinates, targetLatLng) => {
    return new Promise((resolve) => {
      let index = 0;

      // Show "New optimal route found" before starting animation
      setNotification("New optimal route found");
      setTimeout(() => setNotification(null), 2000); // Clear after 2 seconds

      const moveMarker = () => {
        if (index < coordinates.length) {
          const newPosition = [coordinates[index].lat, coordinates[index].lng];
          marker.setLatLng(newPosition);
          mapRef.current.panTo(newPosition);
          setCurrentPosition(newPosition);
          console.log("Marker moved to:", newPosition);

          const distance =
            L.latLng(newPosition).distanceTo(targetLatLng) / 1000;
          console.log(`Distance to ${targetLatLng}: ${distance} km`);

          if (distance < CONFIG.PROXIMITY_THRESHOLD) {
            console.log(`Marker close to ${targetLatLng}, sending signal`);
            // Show "Calculating the best route" when reaching the node
            setNotification("Calculating the best route");
            setTimeout(() => setNotification(null), 2000); // Clear after 2 seconds

            axios
              .post(`${CONFIG.API_BASE_URL}/marker-close`, {
                node: targetLatLng.toString(),
              })
              .then((response) => {
                console.log(
                  "Marker-close signal sent successfully:",
                  response.data
                );
                resolve();
              })
              .catch((err) => {
                console.error("Failed to send marker-close:", err.message);
                setError(`Failed to send marker-close: ${err.message}`);
                resolve();
              });
          } else {
            index++;
            setTimeout(moveMarker, 100);
          }
        } else {
          console.log("Animation completed without reaching threshold");
          resolve();
        }
      };
      moveMarker();
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    resetApp();
    const sourceCoords = getCoordinatesFromPlace(source) || [
      16.4543715, 80.5250379,
    ];
    initializeMap(sourceCoords);
    setCurrentPosition(sourceCoords);
    startOptimization();
  };

  const handlePreferenceChange = (e, key) => {
    setPreferences((prev) => ({
      ...prev,
      [key]: Number(e.target.value),
    }));
  };

  return (
    <div className="app-container">
      <div className="sidebar">
        <h1>aven</h1>
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Start Location</label>
            <div className="input-wrapper">
              <span className="icon">src: </span>
              <input
                type="text"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="Enter start location"
              />
            </div>
          </div>
          <div className="input-group">
            <label>Destination</label>
            <div className="input-wrapper">
              <span className="icon">dst: </span>
              <input
                type="text"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="Enter destination"
              />
            </div>
          </div>
          <div className="preferences">
            <h3>Route Preferences</h3>
            <div className="preference-item">
              <label>Minimize Traffic</label>
              <div className="slider-wrapper">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={preferences.traffic}
                  onChange={(e) => handlePreferenceChange(e, "traffic")}
                />
                <span>{preferences.traffic}%</span>
              </div>
            </div>
            <div className="preference-item">
              <label>Avoid Bad Weather</label>
              <div className="slider-wrapper">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={preferences.weather}
                  onChange={(e) => handlePreferenceChange(e, "weather")}
                />
                <span>{preferences.weather}%</span>
              </div>
            </div>
            <div className="preference-item">
              <label>Prefer Low Elevation</label>
              <div className="slider-wrapper">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={preferences.elevation}
                  onChange={(e) => handlePreferenceChange(e, "elevation")}
                />
                <span>{preferences.elevation}%</span>
              </div>
            </div>
            <div className="preference-item">
              <label>Minimize Air Pollution</label>
              <div className="slider-wrapper">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={preferences.air_quality}
                  onChange={(e) => handlePreferenceChange(e, "air_quality")}
                />
                <span>{preferences.air_quality}%</span>
              </div>
            </div>
          </div>
          <button type="submit" className="start-routing">
            Start Routing
          </button>
        </form>
        {error && <div className="error">{error}</div>}
      </div>
      <div className="map-container">
        {routeData.status === "idle" && (
          <div className="map-placeholder">
            <span className="icon">🗺️</span>
            <p>Enter locations and start routing to see the map</p>
          </div>
        )}
        <div
          id="map"
          style={{ display: routeData.status === "idle" ? "none" : "block" }}
        ></div>
        {notification && <div className="map-notification">{notification}</div>}
      </div>
    </div>
  );
}

export default App;
