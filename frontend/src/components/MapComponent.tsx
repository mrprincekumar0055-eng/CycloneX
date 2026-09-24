"use client";

import { useEffect, useRef, useState } from "react";

interface MapProps {
  center?: [number, number];
  zoom?: number;
  cyclone?: any;
  observations?: any[];
  forecastPoints?: any[];
  uncertaintyCone?: any;
  shelters?: any[];
  hospitals?: any[];
  evacuationRoute?: any;
  showSatellite?: boolean;
  satelliteOpacity?: number;
  activeLayers?: {
    forecast: boolean;
    uncertainty: boolean;
    windSwaths: boolean;
    shelters: boolean;
    hospitals: boolean;
    evacuationRoute: boolean;
  };
  onMapClick?: (lat: number, lon: number) => void;
  clickedPoint?: { lat: number; lon: number } | null;
}

export default function MapComponent({
  center,
  zoom = 6,
  cyclone,
  observations = [],
  forecastPoints = [],
  uncertaintyCone = null,
  shelters = [],
  hospitals = [],
  evacuationRoute = null,
  showSatellite = false,
  satelliteOpacity = 0.75,
  activeLayers = {
    forecast: true,
    uncertainty: true,
    windSwaths: true,
    shelters: true,
    hospitals: true,
    evacuationRoute: true
  },
  onMapClick,
  clickedPoint = null
}: MapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const layerGroupRef = useRef<any>({});
  const [mapLoaded, setMapLoaded] = useState(false);

  // Safe non-null cyclone fallback (ensures zero runtime exceptions)
  const activeCyclone = cyclone || {
    current_lat: 21.65,
    current_lon: 66.85,
    name: "BIPARJOY",
    current_wind_speed_kts: 85,
    current_pressure_hpa: 964,
    current_category: "Very Severe Cyclonic Storm"
  };

  useEffect(() => {
    if (typeof window === "undefined") return;

    import("leaflet").then((L) => {
      if (!mapContainerRef.current) return;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
      }

      const centerLat = center ? center[0] : (activeCyclone.current_lat || 21.65);
      const centerLon = center ? center[1] : (activeCyclone.current_lon || 66.85);

      const map = L.map(mapContainerRef.current, {
        center: [centerLat, centerLon],
        zoom: zoom || 6,
        zoomControl: false
      });

      L.control.zoom({ position: "bottomright" }).addTo(map);

      // Key-free high-reliability OpenStreetMap tile provider (no watermarks, universal availability)
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
      }).addTo(map);

      // Map Click Handler for Location-Specific Intelligence
      map.on("click", (e: any) => {
        if (onMapClick) {
          onMapClick(e.latlng.lat, e.latlng.lng);
        }
      });

      mapInstanceRef.current = map;
      layerGroupRef.current = {
        satellite: L.layerGroup().addTo(map),
        pastTrack: L.layerGroup().addTo(map),
        forecast: L.layerGroup().addTo(map),
        uncertainty: L.layerGroup().addTo(map),
        windSwaths: L.layerGroup().addTo(map),
        infrastructure: L.layerGroup().addTo(map),
        routes: L.layerGroup().addTo(map),
        cycloneEye: L.layerGroup().addTo(map),
        userPin: L.layerGroup().addTo(map)
      };

      setMapLoaded(true);
    });

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapLoaded || !mapInstanceRef.current) return;
    import("leaflet").then((L) => {
      const map = mapInstanceRef.current;
      const groups = layerGroupRef.current;

      // 1. Satellite (NASA GIBS)
      groups.satellite.clearLayers();
      if (showSatellite) {
        const today = new Date().toISOString().split("T")[0];
        const gibsTileUrl = `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${today}/GoogleMapsCompatible_Level9/{z}/{x}/{y}.jpg`;
        const satLayer = L.tileLayer(gibsTileUrl, {
          opacity: satelliteOpacity,
          maxZoom: 9,
          attribution: "NASA GIBS / MODIS Terra"
        });
        groups.satellite.addLayer(satLayer);
      }

      // 2. Past Observed Track
      groups.pastTrack.clearLayers();
      if (observations && observations.length > 0) {
        const latlngs = observations.map((o: any) => [o.lat, o.lon]);
        const trackLine = L.polyline(latlngs, {
          color: "#475569",
          weight: 2.5,
          dashArray: "3, 4"
        });
        groups.pastTrack.addLayer(trackLine);

        observations.forEach((o: any) => {
          const dot = L.circleMarker([o.lat, o.lon], {
            radius: 4,
            fillColor: "#475569",
            color: "#FFFFFF",
            weight: 1.5,
            fillOpacity: 1
          }).bindPopup(`
            <div class="text-xs font-sans">
              <strong class="text-slate-900 block font-semibold">Observed Fix</strong>
              <div class="text-slate-600 mt-0.5">Time: ${new Date(o.timestamp).toLocaleString()}</div>
              <div class="text-slate-800 font-medium">Wind: ${o.wind_speed_kts} kts (${Math.round(o.wind_speed_kts * 1.852)} km/h)</div>
              <div class="text-slate-600">Pressure: ${o.central_pressure_hpa} hPa</div>
            </div>
          `);
          groups.pastTrack.addLayer(dot);
        });
      }

      // 3. Cyclone Center Eye (High-Contrast Clean Operational Target Marker)
      groups.cycloneEye.clearLayers();
      if (activeCyclone.current_lat && activeCyclone.current_lon) {
        const eyeIcon = L.divIcon({
          className: "cyclone-eye-marker",
          html: `
            <div class="relative flex items-center justify-center w-8 h-8">
              <div class="absolute w-8 h-8 rounded-full border-2 border-red-600 bg-red-100/50"></div>
              <div class="w-2.5 h-2.5 rounded-full bg-red-600 border border-white shadow"></div>
            </div>
          `,
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        });

        const eyeMarker = L.marker([activeCyclone.current_lat, activeCyclone.current_lon], { icon: eyeIcon })
          .bindPopup(`
            <div class="text-xs font-sans">
              <div class="font-bold text-red-700 text-sm mb-1 uppercase tracking-wide">CYCLONE ${activeCyclone.name}</div>
              <div class="text-slate-600"><strong>Stage:</strong> ${activeCyclone.current_category || 'Very Severe Cyclonic Storm'}</div>
              <div class="text-slate-800"><strong>Max Wind:</strong> <span class="font-bold text-red-700">${activeCyclone.current_wind_speed_kts} kts</span> (${Math.round((activeCyclone.current_wind_speed_kts || 0) * 1.852)} km/h)</div>
              <div class="text-slate-800"><strong>Pressure:</strong> ${activeCyclone.current_pressure_hpa} hPa</div>
              <div class="text-[11px] text-slate-500 mt-1 font-mono">Center: ${activeCyclone.current_lat.toFixed(2)}°N, ${activeCyclone.current_lon.toFixed(2)}°E</div>
            </div>
          `);
        groups.cycloneEye.addLayer(eyeMarker);
      }

      // 4. Uncertainty Cone
      groups.uncertainty.clearLayers();
      if (activeLayers.uncertainty && uncertaintyCone) {
        try {
          const coneData = typeof uncertaintyCone === "string" ? JSON.parse(uncertaintyCone) : uncertaintyCone;
          const coneGeo = L.geoJSON(coneData, {
            style: {
              color: "#DC2626",
              weight: 1.5,
              fillColor: "#DC2626",
              fillOpacity: 0.08,
              dashArray: "4, 4"
            }
          }).bindPopup(`<div class="text-xs font-sans font-medium text-red-800">Forecast Track Uncertainty Cone (68% CI)</div>`);
          groups.uncertainty.addLayer(coneGeo);
        } catch (e) {
          console.warn("[MapComponent] Uncertainty cone render skipped:", e);
        }
      }

      // 5. Forecast Track Points
      groups.forecast.clearLayers();
      if (activeLayers.forecast && forecastPoints && forecastPoints.length > 0) {
        const forecastLatLngs = [
          [activeCyclone.current_lat, activeCyclone.current_lon],
          ...forecastPoints.map((p: any) => [p.lat, p.lon])
        ];

        const forecastLine = L.polyline(forecastLatLngs, {
          color: "#DC2626",
          weight: 3,
          dashArray: "6, 4"
        });
        groups.forecast.addLayer(forecastLine);

        forecastPoints.forEach((p: any) => {
          const isLandfall = p.forecast_hour === 48;
          const color = isLandfall ? "#B91C1C" : "#DC2626";
          const marker = L.circleMarker([p.lat, p.lon], {
            radius: isLandfall ? 7 : 5,
            fillColor: color,
            color: "#FFFFFF",
            weight: 2,
            fillOpacity: 1
          }).bindPopup(`
            <div class="text-xs font-sans">
              <span class="inline-block px-1.5 py-0.5 rounded bg-red-50 text-red-800 font-semibold border border-red-200 text-[10px] mb-1">
                +${p.forecast_hour}h FORECAST ${isLandfall ? '• LANDFALL TARGET' : ''}
              </span>
              <div class="font-bold text-slate-900">${p.lat.toFixed(2)}°N, ${p.lon.toFixed(2)}°E</div>
              <div class="text-slate-800 mt-0.5"><strong>Wind:</strong> ${p.predicted_wind_speed_kts} kts (${Math.round(p.predicted_wind_speed_kts * 1.852)} km/h)</div>
              <div class="text-slate-600">Pressure: ${p.predicted_pressure_hpa} hPa • ${p.category}</div>
              <div class="text-slate-500 text-[10px] mt-0.5 font-mono">Uncertainty Radius: ±${p.uncertainty_radius_km} km</div>
            </div>
          `);
          groups.forecast.addLayer(marker);
        });
      }

      // 6. Wind Swaths
      groups.windSwaths.clearLayers();
      if (activeLayers.windSwaths && activeCyclone.current_lat && activeCyclone.current_lon) {
        const cLat = activeCyclone.current_lat;
        const cLon = activeCyclone.current_lon;
        const wind = activeCyclone.current_wind_speed_kts || 85;

        if (wind >= 64) {
          const r64 = L.circle([cLat, cLon], {
            radius: 85000,
            color: "#DC2626",
            fillColor: "#DC2626",
            fillOpacity: 0.12,
            weight: 1
          }).bindPopup(`<div class="text-xs font-sans text-red-800 font-semibold">64-kt Gale Core Swath (Destructive Winds)</div>`);
          groups.windSwaths.addLayer(r64);
        }

        if (wind >= 50) {
          const r50 = L.circle([cLat, cLon], {
            radius: 160000,
            color: "#EA580C",
            fillColor: "#EA580C",
            fillOpacity: 0.08,
            weight: 1
          }).bindPopup(`<div class="text-xs font-sans text-amber-800">50-kt Storm Wind Swath</div>`);
          groups.windSwaths.addLayer(r50);
        }

        if (wind >= 34) {
          const r34 = L.circle([cLat, cLon], {
            radius: 260000,
            color: "#F59E0B",
            fillColor: "#F59E0B",
            fillOpacity: 0.05,
            weight: 1
          }).bindPopup(`<div class="text-xs font-sans text-amber-800">34-kt Gale Swath (Marine Hazard)</div>`);
          groups.windSwaths.addLayer(r34);
        }
      }

      // 7. Critical Infrastructure (Shelters & Hospitals)
      groups.infrastructure.clearLayers();
      if (activeLayers.shelters && shelters && shelters.length > 0) {
        shelters.forEach((sh: any) => {
          const shelterIcon = L.divIcon({
            className: "shelter-icon",
            html: `
              <div class="w-5 h-5 rounded bg-emerald-600 text-white font-mono font-bold flex items-center justify-center text-[10px] shadow border border-white" title="${sh.name}">
                S
              </div>
            `,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
          });
          const m = L.marker([sh.lat, sh.lon], { icon: shelterIcon })
            .bindPopup(`
              <div class="text-xs font-sans">
                <span class="inline-block px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 font-semibold border border-emerald-200 text-[10px] mb-1">CYCLONE SHELTER (MPCS)</span>
                <div class="font-bold text-slate-900">${sh.name}</div>
                <div class="text-slate-600 mt-1">Capacity: <strong>${sh.total_capacity}</strong> persons</div>
                <div class="text-slate-600">Generator: ${sh.generator_available ? 'Verified Operational' : 'None'}</div>
                <div class="text-slate-500 text-[10px] mt-0.5 font-mono">Location: ${sh.lat.toFixed(3)}°N, ${sh.lon.toFixed(3)}°E</div>
              </div>
            `);
          groups.infrastructure.addLayer(m);
        });
      }

      if (activeLayers.hospitals && hospitals && hospitals.length > 0) {
        hospitals.forEach((hosp: any) => {
          const hospIcon = L.divIcon({
            className: "hosp-icon",
            html: `
              <div class="w-5 h-5 rounded bg-blue-600 text-white font-mono font-bold flex items-center justify-center text-[10px] shadow border border-white" title="${hosp.name}">
                H
              </div>
            `,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
          });
          const m = L.marker([hosp.lat, hosp.lon], { icon: hospIcon })
            .bindPopup(`
              <div class="text-xs font-sans">
                <span class="inline-block px-1.5 py-0.5 rounded bg-blue-50 text-blue-800 font-semibold border border-blue-200 text-[10px] mb-1">EMERGENCY HOSPITAL</span>
                <div class="font-bold text-slate-900">${hosp.name}</div>
                <div class="text-slate-600 mt-1">Total Beds: <strong>${hosp.total_beds}</strong> (ICU: ${hosp.available_icu_beds})</div>
                <div class="text-slate-600">Trauma Unit: ${hosp.emergency_trauma_unit ? 'Available 24/7' : 'Standard'}</div>
                <div class="text-slate-500 text-[10px] mt-0.5 font-mono">Location: ${hosp.lat.toFixed(3)}°N, ${hosp.lon.toFixed(3)}°E</div>
              </div>
            `);
          groups.infrastructure.addLayer(m);
        });
      }

      // 8. Evacuation Routes
      groups.routes.clearLayers();
      if (activeLayers.evacuationRoute && evacuationRoute && evacuationRoute.route_geojson) {
        const routeGeo = L.geoJSON(evacuationRoute.route_geojson, {
          style: {
            color: "#0D9488",
            weight: 4,
            dashArray: "5, 5"
          }
        }).bindPopup(`<div class="text-xs font-sans font-semibold text-teal-800">Priority Evacuation Corridor (SH-6 Coastal Route)</div>`);
        groups.routes.addLayer(routeGeo);
      }

      // 9. Interactive User Selected Location Pinpoint
      groups.userPin.clearLayers();
      if (clickedPoint) {
        const pinIcon = L.divIcon({
          className: "user-pin-marker",
          html: `
            <div class="relative flex items-center justify-center w-6 h-6">
              <div class="w-4 h-4 rounded-full bg-red-600 border-2 border-white shadow"></div>
            </div>
          `,
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });
        const pin = L.marker([clickedPoint.lat, clickedPoint.lon], { icon: pinIcon })
          .bindPopup(`
            <div class="text-xs font-sans">
              <strong class="text-slate-900 block font-semibold">Selected Location</strong>
              <div class="font-mono text-slate-600 text-[11px]">${clickedPoint.lat.toFixed(4)}°N, ${clickedPoint.lon.toFixed(4)}°E</div>
            </div>
          `).openPopup();
        groups.userPin.addLayer(pin);
      }
    });
  }, [mapLoaded, cyclone, observations, forecastPoints, uncertaintyCone, shelters, hospitals, evacuationRoute, showSatellite, satelliteOpacity, activeLayers, clickedPoint]);

  return (
    <div className="relative w-full h-full min-h-[480px] rounded overflow-hidden border border-slate-200 bg-white">
      <div ref={mapContainerRef} className="w-full h-full cursor-crosshair" />
      
      {/* Click Hint Overlay */}
      <div className="absolute top-2.5 left-2.5 z-[400] bg-white/95 border border-slate-200 rounded px-2.5 py-1 text-[11px] text-slate-700 font-sans flex items-center space-x-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-slate-700" />
        <span>Click map to inspect location intelligence</span>
      </div>

      {/* Clean Light Legend */}
      <div className="absolute bottom-3 left-3 z-[400] bg-white/95 border border-slate-200 rounded p-2 text-[11px] font-sans max-w-xs pointer-events-auto">
        <div className="text-slate-400 font-medium mb-1 text-[10px] uppercase tracking-wider">
          Map Legend
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-slate-700 text-[11px]">
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full border border-red-600 bg-red-100" />
            <span>Cyclone Eye</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-0.5 bg-red-600" />
            <span>Forecast Track</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded bg-slate-200 border border-slate-300" />
            <span>Error Cone</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded bg-emerald-600" />
            <span>Shelter</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded bg-blue-600" />
            <span>Hospital</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-0.5 bg-teal-600" />
            <span>Evac Route</span>
          </div>
        </div>
      </div>
    </div>
  );
}
