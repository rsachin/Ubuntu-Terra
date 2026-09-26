import { useEffect, useRef, useState } from "react";
import { Map as MapLibreMap, NavigationControl, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { SearchIcon, PinIcon, MicIcon, CameraIcon } from "./Icons";

const SATELLITE_STYLE = {
  version: 8,
  sources: {
    "esri-satellite": {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      attribution: "Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
    },
  },
  layers: [
    {
      id: "esri-satellite-layer",
      type: "raster",
      source: "esri-satellite",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

const RISK_COLOR = {
  Low: "#00d2d3",
  Medium: "#ff9f43",
  High: "#ff5252",
};

export default function FieldMap({
  fields,
  selectedFieldId,
  riskByFieldId,
  onSelect,
  onAddField,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef({});

  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [isMicActive, setIsMicActive] = useState(false);

  const [isDrawing, setIsDrawing] = useState(false);
  const [drawPoints, setDrawPoints] = useState([]);
  const [fieldName, setFieldName] = useState("");
  const [saving, setSaving] = useState(false);
  const [drawError, setDrawError] = useState("");

  const isDrawingRef = useRef(isDrawing);
  isDrawingRef.current = isDrawing;

  // Map initialization with Esri satellite base layer
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new MapLibreMap({
      container: containerRef.current,
      style: SATELLITE_STYLE,
      center: [24.95, -33.65],
      zoom: 9.5,
      attributionControl: true,
    });

    map.addControl(new NavigationControl({ showCompass: false }), "top-right");

    map.on("load", () => {
      // GeoJSON polygon boundary layer for fields with subtle neon outlines
      if (!map.getSource("fields-src")) {
        map.addSource("fields-src", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });

        map.addLayer({
          id: "fields-fill",
          type: "fill",
          source: "fields-src",
          paint: {
            "fill-color": ["coalesce", ["get", "color"], "#00d2d3"],
            "fill-opacity": 0.28,
          },
        });

        map.addLayer({
          id: "fields-line",
          type: "line",
          source: "fields-src",
          paint: {
            "line-color": ["coalesce", ["get", "color"], "#00d2d3"],
            "line-width": 3,
            "line-blur": 1,
          },
        });
      }

      // Drawing layer
      if (!map.getSource("drawing-src")) {
        map.addSource("drawing-src", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });

        map.addLayer({
          id: "drawing-fill",
          type: "fill",
          source: "drawing-src",
          filter: ["==", "$type", "Polygon"],
          paint: {
            "fill-color": "#2ed573",
            "fill-opacity": 0.35,
          },
        });

        map.addLayer({
          id: "drawing-line",
          type: "line",
          source: "drawing-src",
          paint: {
            "line-color": "#2ed573",
            "line-width": 3,
            "line-dasharray": [2, 1],
          },
        });

        map.addLayer({
          id: "drawing-pts",
          type: "circle",
          source: "drawing-src",
          filter: ["==", "$type", "Point"],
          paint: {
            "circle-radius": 7,
            "circle-color": "#2ed573",
            "circle-stroke-width": 2,
            "circle-stroke-color": "#FFFFFF",
          },
        });
      }
    });

    map.on("click", (e) => {
      if (!isDrawingRef.current) return;
      const pt = [e.lngLat.lng, e.lngLat.lat];
      setDrawPoints((prev) => [...prev, pt]);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update drawing overlay
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const updateDrawing = () => {
      const src = map.getSource("drawing-src");
      if (!src) return;

      const features = [];
      if (drawPoints.length > 0) {
        drawPoints.forEach((pt) => {
          features.push({
            type: "Feature",
            geometry: { type: "Point", coordinates: pt },
          });
        });

        if (drawPoints.length >= 2) {
          features.push({
            type: "Feature",
            geometry: { type: "LineString", coordinates: drawPoints },
          });
        }

        if (drawPoints.length >= 3) {
          features.push({
            type: "Feature",
            geometry: {
              type: "Polygon",
              coordinates: [[...drawPoints, drawPoints[0]]],
            },
          });
        }
      }

      src.setData({ type: "FeatureCollection", features });
    };

    if (map.isStyleLoaded()) updateDrawing();
    else map.once("load", updateDrawing);
  }, [drawPoints]);

  // Render field polygons and custom SVG teardrop pin markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !fields?.length) return;

    const updateFields = () => {
      const fieldsSrc = map.getSource("fields-src");
      if (fieldsSrc) {
        const polygonFeatures = fields.map((f) => {
          const risk = riskByFieldId?.[f.id];
          const color = risk ? RISK_COLOR[risk] : "#00d2d3";
          return {
            type: "Feature",
            properties: { id: f.id, name: f.name, color },
            geometry: f.boundary,
          };
        });
        fieldsSrc.setData({
          type: "FeatureCollection",
          features: polygonFeatures,
        });
      }

      Object.values(markersRef.current).forEach((m) => m.remove());
      markersRef.current = {};

      fields.forEach((field) => {
        const [lon, lat] = centroid(field.boundary);
        const risk = riskByFieldId?.[field.id] || "Low";
        const selected = field.id === selectedFieldId;

        const el = createPinElement(risk, selected, () => onSelect(field.id));

        const marker = new Marker({ element: el, anchor: "bottom" })
          .setLngLat([lon, lat])
          .addTo(map);
        markersRef.current[field.id] = marker;
      });
    };

    if (map.isStyleLoaded()) updateFields();
    else map.once("load", updateFields);
  }, [fields, selectedFieldId, riskByFieldId, onSelect]);

  // Place Search via Nominatim
  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    setSearchError("");

    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&countrycodes=za&q=${encodeURIComponent(
        searchQuery,
      )}`;
      const res = await fetch(url);
      const data = await res.json();
      if (!data || data.length === 0) {
        setSearchError("No South African locations found for that search.");
      } else {
        const top = data[0];
        const lat = parseFloat(top.lat);
        const lon = parseFloat(top.lon);
        if (mapRef.current) {
          mapRef.current.flyTo({ center: [lon, lat], zoom: 13.5 });
        }
      }
    } catch {
      setSearchError("Location search service unavailable. Please try again.");
    } finally {
      setSearching(false);
    }
  };

  const handleMicToggle = () => {
    setIsMicActive((prev) => !prev);
    if (!isMicActive && typeof window !== "undefined") {
      const Recognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      if (Recognition) {
        const recognition = new Recognition();
        recognition.lang = "en-ZA";
        recognition.onresult = (e) => {
          const text = e.results[0][0].transcript;
          setSearchQuery(text);
          setIsMicActive(false);
        };
        recognition.onerror = () => setIsMicActive(false);
        recognition.start();
      }
    }
  };

  const handleLocateMe = () => {
    if (navigator.geolocation && mapRef.current) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          mapRef.current.flyTo({
            center: [pos.coords.longitude, pos.coords.latitude],
            zoom: 14,
          });
        },
        () => {
          // Fallback to Kirkwood demo center
          mapRef.current.flyTo({ center: [25.43, -33.40], zoom: 13.5 });
        },
      );
    }
  };

  const handleStartDraw = () => {
    setIsDrawing(true);
    setDrawPoints([]);
    setFieldName("");
    setDrawError("");
  };

  const handleCancelDraw = () => {
    setIsDrawing(false);
    setDrawPoints([]);
    setFieldName("");
    setDrawError("");
  };

  const handleSaveField = async (e) => {
    e.preventDefault();
    if (!fieldName.trim()) {
      setDrawError("Please enter a field name.");
      return;
    }
    if (drawPoints.length < 3) {
      setDrawError("Please click at least 3 points on the map to define your field boundary.");
      return;
    }

    setSaving(true);
    setDrawError("");

    try {
      const closedCoordinates = [[...drawPoints, drawPoints[0]]];
      const boundary_geojson = {
        type: "Polygon",
        coordinates: closedCoordinates,
      };

      await onAddField({ name: fieldName.trim(), boundary_geojson });
      setIsDrawing(false);
      setDrawPoints([]);
      setFieldName("");
    } catch (err) {
      setDrawError(err.message || "Failed to save field boundary.");
    } finally {
      setSaving(false);
    }
  };

  const scrollToCamera = () => {
    const el = document.getElementById("photo-upload-section");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="field-map-wrapper">
      {/* Search Bar Pill Container overlaying the top-left of the map */}
      <form onSubmit={handleSearch} className="map-pill-search">
        <span className="map-pill-search__icon">
          <SearchIcon size={18} />
        </span>
        <input
          type="text"
          placeholder="Search your town or farm..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="map-pill-search__input"
        />
        <div className="map-pill-search__actions">
          <button
            type="button"
            className="map-pill-btn map-pill-btn--pin"
            onClick={handleLocateMe}
            title="Locate my farm"
          >
            <PinIcon size={16} />
          </button>
          <button
            type="button"
            className={`map-pill-btn map-pill-btn--mic${isMicActive ? " is-active" : ""}`}
            onClick={handleMicToggle}
            title="Voice search"
          >
            <MicIcon size={16} />
          </button>
        </div>
      </form>

      {/* Floating Action Button for drawing a new field boundary */}
      {!isDrawing && (
        <button
          type="button"
          className="map-draw-fab"
          onClick={handleStartDraw}
          title="Draw New Field Boundary"
          aria-label="Draw New Field Boundary"
        >
          ✏️ Draw New Field Boundary
        </button>
      )}

      {/* Floating Action Button (FAB) for Camera */}
      <button
        type="button"
        className="camera-fab"
        onClick={scrollToCamera}
        title="Upload crop photo for pest diagnosis"
        aria-label="Upload crop photo"
      >
        <CameraIcon size={24} />
      </button>

      {searchError && <div className="app__banner">{searchError}</div>}

      {/* Drawing Controls Overlay */}
      {isDrawing ? (
        <div className="drawing-bar">
          <div className="drawing-info">
            <strong>Drawing Mode:</strong> Click on map to add boundary points ({drawPoints.length} added)
          </div>

          <div className="drawing-actions">
            {drawPoints.length > 0 && (
              <button onClick={() => setDrawPoints((prev) => prev.slice(0, -1))} className="drawing-btn">
                ↩️ Undo
              </button>
            )}
            <button onClick={handleCancelDraw} className="drawing-btn">
              ❌ Cancel
            </button>
          </div>

          {drawPoints.length >= 3 && (
            <form onSubmit={handleSaveField} className="drawing-save-form">
              <input
                type="text"
                placeholder="Field name (e.g. Ceres Orchard Block 4)"
                value={fieldName}
                onChange={(e) => setFieldName(e.target.value)}
                className="drawing-name-input"
                required
              />
              <button type="submit" disabled={saving} className="drawing-save-btn">
                {saving ? "Saving…" : "💾 Save Field"}
              </button>
            </form>
          )}
        </div>
      ) : null}

      {drawError && <div className="app__banner">{drawError}</div>}

      <div
        ref={containerRef}
        className="field-map"
        role="img"
        aria-label="Satellite map of field boundaries and risk indicators"
      />
    </div>
  );
}

// Helper to generate SVG teardrop pins with embedded risk icons & glow shadows
function createPinElement(risk, isSelected, onClick) {
  const container = document.createElement("button");
  container.className = `map-pin-container map-pin-${(risk || "Low").toLowerCase()}`;
  container.setAttribute("aria-label", `Select field pin`);
  container.onclick = onClick;

  const pinColor = risk === "High" ? "#ff5252" : risk === "Medium" ? "#ff9f43" : "#00d2d3";
  const glowShadow =
    risk === "High"
      ? "0 4px 16px rgba(255,82,82,0.7)"
      : risk === "Medium"
      ? "0 4px 16px rgba(255,159,67,0.7)"
      : "0 4px 16px rgba(0,210,211,0.7)";

  let iconSvg = "";
  if (risk === "High") {
    // Prohibited / circle-slash icon
    iconSvg = `<circle cx="15" cy="14" r="5" fill="none" stroke="#ffffff" stroke-width="1.8"/><line x1="11.5" y1="10.5" x2="18.5" y2="17.5" stroke="#ffffff" stroke-width="1.8"/>`;
  } else if (risk === "Medium") {
    // Warning triangle icon
    iconSvg = `<path d="M15 8L20.5 18H9.5L15 8Z" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-linejoin="round"/><line x1="15" y1="11.5" x2="15" y2="14.5" stroke="#ffffff" stroke-width="1.8"/><circle cx="15" cy="16.5" r="0.7" fill="#ffffff"/>`;
  } else {
    // Low risk: Water drop icon
    iconSvg = `<path d="M15 8.5C15 8.5 10.5 13 10.5 15.2C10.5 17.6 12.5 19.5 15 19.5C17.5 19.5 19.5 17.6 19.5 15.2C19.5 13 15 8.5 15 8.5Z" fill="none" stroke="#ffffff" stroke-width="1.8"/>`;
  }

  const borderStroke = isSelected ? "#ffffff" : "rgba(255,255,255,0.4)";
  const borderWidth = isSelected ? "3" : "1.5";

  container.innerHTML = `
    <svg width="36" height="46" viewBox="0 0 30 40" class="map-pin-svg" style="filter: drop-shadow(${glowShadow}); overflow: visible;">
      <!-- Teardrop Pin Shape (rounded top, pointed bottom) -->
      <path d="M15 2 C7.82 2 2 7.82 2 15 C2 24.5 15 38 15 38 C15 38 28 24.5 28 15 C28 7.82 22.18 2 15 2 Z"
            fill="${pinColor}"
            stroke="${borderStroke}"
            stroke-width="${borderWidth}"
      />
      <!-- Icon centered in the top portion -->
      ${iconSvg}
    </svg>
  `;

  return container;
}

function centroid(geojsonPolygon) {
  const ring = geojsonPolygon.coordinates[0];
  const lon = ring.reduce((sum, [x]) => sum + x, 0) / ring.length;
  const lat = ring.reduce((sum, [, y]) => sum + y, 0) / ring.length;
  return [lon, lat];
}
