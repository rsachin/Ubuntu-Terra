import { useEffect, useRef } from "react";
import { Map as MapLibreMap, NavigationControl, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const RISK_COLOR = {
  Low: "#1B6E6E",
  Medium: "#B4741F",
  High: "#A13A2A",
};

// Inline raster style pointing directly at OSM tiles — no external
// style.json fetch to fail. demotiles.maplibre.org proved unreliable
// (browser reported "There is no style added to the map").
const STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm-layer", type: "raster", source: "osm" }],
};

export default function FieldMap({
  fields,
  selectedFieldId,
  riskByFieldId,
  onSelect,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef({});

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new MapLibreMap({
      container: containerRef.current,
      style: STYLE,
      center: [24.95, -33.65],
      zoom: 8.3,
      attributionControl: true,
    });
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;

    return () => map.remove();
  }, []);

  // Draw / update field markers whenever the field list or risk data changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !fields?.length) return;

    const draw = () => {
      Object.values(markersRef.current).forEach((m) => m.remove());
      markersRef.current = {};

      fields.forEach((field) => {
        const [lon, lat] = centroid(field.boundary);
        const risk = riskByFieldId?.[field.id];
        const color = risk ? RISK_COLOR[risk] : "#8B8570";

        const el = document.createElement("button");
        el.setAttribute("aria-label", `Select ${field.name}`);
        el.style.width = "22px";
        el.style.height = "22px";
        el.style.borderRadius = "50%";
        el.style.border =
          field.id === selectedFieldId
            ? "3px solid #1E2A22"
            : "2px solid #FBFAF3";
        el.style.background = color;
        el.style.boxShadow = "0 1px 4px rgba(0,0,0,0.35)";
        el.style.cursor = "pointer";
        el.style.padding = 0;
        el.onclick = () => onSelect(field.id);

        const marker = new Marker({ element: el })
          .setLngLat([lon, lat])
          .addTo(map);
        markersRef.current[field.id] = marker;
      });
    };

    if (map.isStyleLoaded()) draw();
    else map.once("load", draw);
  }, [fields, selectedFieldId, riskByFieldId, onSelect]);

  return (
    <div
      ref={containerRef}
      className="field-map"
      role="img"
      aria-label="Map of demo field locations"
    />
  );
}

function centroid(geojsonPolygon) {
  const ring = geojsonPolygon.coordinates[0];
  const lon = ring.reduce((sum, [x]) => sum + x, 0) / ring.length;
  const lat = ring.reduce((sum, [, y]) => sum + y, 0) / ring.length;
  return [lon, lat];
}
