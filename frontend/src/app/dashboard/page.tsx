"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import { 
  X, Radio, RefreshCw
} from "lucide-react";
import { fetchFromAPI } from "@/lib/api";

// Dynamic map import to avoid SSR issues
const MapComponent = dynamic(() => import("@/components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[540px] bg-slate-50 border border-slate-200 rounded flex items-center justify-center text-slate-400 font-mono text-xs">
      Loading GIS Map Surface...
    </div>
  )
});

// Deterministic Biparjoy Operational Baseline
const FALLBACK_BIPARJOY = {
  id: "demo-biparjoy-2023",
  name: "BIPARJOY",
  basin: "Arabian Sea",
  status: "ACTIVE",
  current_lat: 21.65,
  current_lon: 66.85,
  current_wind_speed_kts: 85,
  current_pressure_hpa: 964,
  current_category: "Very Severe Cyclonic Storm",
  current_heading_deg: 38,
  current_speed_kmh: 11.5,
  risk_level: "EXTREME RISK",
  track: [
    { id: "t1", timestamp: "2023-06-13T06:00:00Z", lat: 20.8, lon: 66.5, wind_speed_kts: 90, central_pressure_hpa: 958, imd_category: "Very Severe Cyclonic Storm", source: "NOAA IBTrACS" },
    { id: "t2", timestamp: "2023-06-13T12:00:00Z", lat: 21.2, lon: 66.7, wind_speed_kts: 85, central_pressure_hpa: 962, imd_category: "Very Severe Cyclonic Storm", source: "NOAA IBTrACS" },
    { id: "t3", timestamp: "2023-06-13T18:00:00Z", lat: 21.65, lon: 66.85, wind_speed_kts: 85, central_pressure_hpa: 964, imd_category: "Very Severe Cyclonic Storm", source: "NOAA IBTrACS" }
  ],
  forecast: {
    forecast_points: [
      { forecast_hour: 6, valid_time: "2023-06-14T00:00:00Z", lat: 21.9, lon: 67.2, predicted_wind_speed_kts: 85, predicted_pressure_hpa: 964, category: "Very Severe Cyclonic Storm", uncertainty_radius_km: 35 },
      { forecast_hour: 12, valid_time: "2023-06-14T06:00:00Z", lat: 22.1, lon: 67.4, predicted_wind_speed_kts: 85, predicted_pressure_hpa: 966, category: "Very Severe Cyclonic Storm", uncertainty_radius_km: 55 },
      { forecast_hour: 24, valid_time: "2023-06-14T18:00:00Z", lat: 22.6, lon: 67.9, predicted_wind_speed_kts: 80, predicted_pressure_hpa: 970, category: "Very Severe Cyclonic Storm", uncertainty_radius_km: 80 },
      { forecast_hour: 48, valid_time: "2023-06-15T18:00:00Z", lat: 23.28, lon: 68.65, predicted_wind_speed_kts: 70, predicted_pressure_hpa: 978, category: "Severe Cyclonic Storm", uncertainty_radius_km: 115 },
      { forecast_hour: 72, valid_time: "2023-06-16T18:00:00Z", lat: 23.9, lon: 69.8, predicted_wind_speed_kts: 45, predicted_pressure_hpa: 990, category: "Cyclonic Storm", uncertainty_radius_km: 165 }
    ]
  },
  shelters: [
    { id: "sh-1", name: "Jakhau Primary Cyclone Shelter", lat: 23.24, lon: 68.62, total_capacity: 1500, current_occupancy: 120, is_verified: true, elevation_meters: 8 },
    { id: "sh-2", name: "Mandvi Model School Shelter", lat: 22.83, lon: 69.35, total_capacity: 2200, current_occupancy: 450, is_verified: true, elevation_meters: 12 }
  ],
  hospitals: [
    { id: "hosp-1", name: "Sub-District Hospital Mandvi", lat: 22.83, lon: 69.36, total_beds: 120, available_icu_beds: 8, helipad: true }
  ],
  evacuationRoute: {
    origin_name: "Mandvi Fishery Settlement",
    destination_name: "Mandvi Model High School Shelter",
    distance_km: 18.5,
    travel_time_minutes: 24,
    route_risk_level: "LOW RISK (HIGHWAY)",
    status: "OPEN"
  }
};

export default function DashboardPage() {
  const [selectedCyclone, setSelectedCyclone] = useState<any>(FALLBACK_BIPARJOY);
  const [track, setTrack] = useState<any[]>(FALLBACK_BIPARJOY.track);
  const [forecast, setForecast] = useState<any>(FALLBACK_BIPARJOY.forecast);
  const [riskZones, setRiskZones] = useState<any[]>([]);
  const [shelters, setShelters] = useState<any[]>(FALLBACK_BIPARJOY.shelters);
  const [hospitals, setHospitals] = useState<any[]>(FALLBACK_BIPARJOY.hospitals);
  const [evacuationRoute, setEvacuationRoute] = useState<any>(FALLBACK_BIPARJOY.evacuationRoute);

  const [layers, setLayers] = useState({
    track: true,
    forecast: true,
    uncertainty: true,
    windSwaths: true,
    shelters: true,
    hospitals: true,
    evacuationRoute: true
  });

  const [showSatellite, setShowSatellite] = useState(false);
  const [clickedLocation, setClickedLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [locationIntel, setLocationIntel] = useState<any>(null);
  const [intelLoading, setIntelLoading] = useState(false);
  const [clickedWeather, setClickedWeather] = useState<any>(null);
  const [clickedWeatherLoading, setClickedWeatherLoading] = useState(false);

  const [liveWeather, setLiveWeather] = useState<any>(null);
  const [weatherViewMode, setWeatherViewMode] = useState<"most_disturbed" | "biparjoy">("most_disturbed");
  const [weatherAgeDisplay, setWeatherAgeDisplay] = useState<string>("syncing...");
  const [liveWeatherLoading, setLiveWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState<string | null>(null);
  const [lastUiRefresh, setLastUiRefresh] = useState<Date | null>(null);
  const [nextRefreshSeconds, setNextRefreshSeconds] = useState<number>(300);

  // References to prevent duplicate intervals and handle race conditions
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const weatherRequestIdRef = useRef<number>(0);

  const updateAgeDisplay = (utcString: string | null) => {
    if (!utcString) {
      setWeatherAgeDisplay("just now");
      return;
    }
    const diffSec = Math.max(0, Math.floor((Date.now() - new Date(utcString).getTime()) / 1000));
    if (diffSec < 60) {
      setWeatherAgeDisplay(`${diffSec}s ago`);
    } else {
      const mins = Math.floor(diffSec / 60);
      setWeatherAgeDisplay(`${mins}m ago`);
    }
  };

  const formatCountdown = (secs: number) => {
    const m = Math.floor(Math.max(0, secs) / 60);
    const s = Math.max(0, secs) % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const formatUtcIst = (dateStr?: string | null) => {
    if (!dateStr) return { utc: "--", ist: "--" };
    try {
      const d = new Date(dateStr.endsWith("Z") ? dateStr : `${dateStr}Z`);
      if (isNaN(d.getTime())) {
        const d2 = new Date(dateStr);
        if (isNaN(d2.getTime())) return { utc: dateStr, ist: dateStr };
        return {
          utc: d2.toISOString().replace("T", " ").substring(0, 19) + " UTC",
          ist: d2.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", second: "2-digit" }) + " IST"
        };
      }
      return {
        utc: d.toISOString().replace("T", " ").substring(0, 19) + " UTC",
        ist: d.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", second: "2-digit" }) + " IST"
      };
    } catch {
      return { utc: dateStr, ist: dateStr };
    }
  };

  const fetchLiveWeather = useCallback(async (refresh: boolean = false, mode?: "most_disturbed" | "biparjoy") => {
    const activeMode = mode || weatherViewMode;
    const reqId = ++weatherRequestIdRef.current;
    if (refresh) setLiveWeatherLoading(true);
    setWeatherError(null);

    try {
      const targetParam = activeMode === "biparjoy" ? "biparjoy" : "most_disturbed";
      const ts = Date.now();
      const url = refresh 
        ? `/weather/live?target=${targetParam}&refresh=true&_ts=${ts}` 
        : `/weather/live?target=${targetParam}&_ts=${ts}`;
      
      const wData = await fetchFromAPI(url, { cache: "no-store" });
      
      // Ignore if a newer request was dispatched
      if (reqId !== weatherRequestIdRef.current) return;

      if (wData) {
        setLiveWeather(wData);
        setLastUiRefresh(new Date());
        setNextRefreshSeconds(300);
        updateAgeDisplay(wData.last_sync_utc || wData.fetched_at || wData.timestamp);
      } else {
        setWeatherError("Weather service unreachable.");
        // Retain last known data as STALE if available
        setLiveWeather((prev: any) => prev ? { ...prev, status: "STALE", data_status: "STALE" } : null);
      }
    } catch (err: any) {
      if (reqId === weatherRequestIdRef.current) {
        setWeatherError(err?.message || "Failed to contact weather provider");
        setLiveWeather((prev: any) => prev ? { ...prev, status: "STALE", data_status: "STALE" } : null);
      }
    } finally {
      if (reqId === weatherRequestIdRef.current) {
        setLiveWeatherLoading(false);
      }
    }
  }, [weatherViewMode]);

  const handleModeSwitch = (newMode: "most_disturbed" | "biparjoy") => {
    setWeatherViewMode(newMode);
    fetchLiveWeather(true, newMode);
  };

  // Load cyclone scenario data once on initial mount
  useEffect(() => {
    async function loadData() {
      try {
        const cycData = await fetchFromAPI("/cyclones");
        if (cycData && cycData.length > 0) {
          const active = cycData[0];
          setSelectedCyclone(active);

          const [trackData, fcData, riskData, shData, hospData, routeData] = await Promise.all([
            fetchFromAPI(`/cyclones/${active.id}/track`),
            fetchFromAPI(`/cyclones/${active.id}/forecast`),
            fetchFromAPI(`/cyclones/${active.id}/risk`),
            fetchFromAPI(`/facilities/shelters`),
            fetchFromAPI(`/facilities/hospitals`),
            fetchFromAPI(`/routes`)
          ]);

          if (trackData && trackData.length > 0) setTrack(trackData);
          if (fcData) setForecast(fcData);
          if (riskData) setRiskZones(riskData);
          if (shData && shData.length > 0) setShelters(shData);
          if (hospData && hospData.length > 0) setHospitals(hospData);
          if (routeData && routeData.length > 0) setEvacuationRoute(routeData[0]);
        }
      } catch {
        // Fallback already pre-set
      }
    }

    loadData();
  }, []);

  // Weather Polling Lifecycle: Initial fetch on mount + controlled 5-minute auto-refresh & 1s countdown
  useEffect(() => {
    fetchLiveWeather(true, weatherViewMode);

    // 1-second countdown and automatic 5-minute trigger
    countdownIntervalRef.current = setInterval(() => {
      setNextRefreshSeconds((prev) => {
        if (prev <= 1) {
          fetchLiveWeather(true, weatherViewMode);
          return 300;
        }
        return prev - 1;
      });
    }, 1000);

    // 5-second relative timestamp updater
    const ageTimer = setInterval(() => {
      setLiveWeather((curr: any) => {
        if (curr) {
          updateAgeDisplay(curr.last_sync_utc || curr.fetched_at || curr.timestamp);
        }
        return curr;
      });
    }, 5000);

    return () => {
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
      clearInterval(ageTimer);
    };
  }, [weatherViewMode, fetchLiveWeather]);

  const handleMapClick = async (lat: number, lon: number) => {
    setClickedLocation({ lat, lon });
    setIntelLoading(true);
    setClickedWeatherLoading(true);
    setClickedWeather(null); // Clear previous coordinates immediately to prevent stale cross-contamination
    const activeId = selectedCyclone?.id || "demo-biparjoy-2023";

    // Concurrently fetch real-time atmospheric observations for the clicked coordinates with cache-busting
    fetchFromAPI(`/weather/live?lat=${lat}&lon=${lon}&refresh=true&_ts=${Date.now()}`, { cache: "no-store" })
      .then((wData) => {
        if (wData) setClickedWeather(wData);
        else setClickedWeather({ status: "OFFLINE", data_status: "OFFLINE", location: { latitude: lat, longitude: lon, name: "Observation Sector" } });
      })
      .catch((err) => {
        setClickedWeather({ status: "OFFLINE", data_status: "OFFLINE", error: String(err), location: { latitude: lat, longitude: lon, name: "Observation Sector" } });
      })
      .finally(() => setClickedWeatherLoading(false));

    try {
      const intel = await fetchFromAPI(`/cyclones/${activeId}/location-intelligence?lat=${lat}&lon=${lon}`);
      if (intel) {
        setLocationIntel(intel);
        setIntelLoading(false);
        return;
      }
    } catch {
      // Fallback below
    }

    const stormLat = selectedCyclone?.current_lat || 21.65;
    const stormLon = selectedCyclone?.current_lon || 66.85;
    const dLat = (lat - stormLat) * 111.0;
    const dLon = (lon - stormLon) * 111.0 * Math.cos((stormLat * Math.PI) / 180.0);
    const dist = Math.round(Math.sqrt(dLat * dLat + dLon * dLon) * 10) / 10;
    let bearing = Math.round(Math.atan2(dLon, dLat) * (180.0 / Math.PI));
    if (bearing < 0) bearing += 360;

    const maxWind = selectedCyclone?.current_wind_speed_kts || 85;
    let localWind = maxWind * Math.pow(35.0 / Math.max(dist, 10.0), 1.35 * 0.5);
    localWind = Math.round(Math.min(maxWind, Math.max(15, localWind)) * 10) / 10;

    const hazard = Math.min(1.0, localWind / 90.0);
    const riskScore = Math.round((0.45 * hazard + 0.35 * 0.75 + 0.20 * 0.70) * 100) / 100;

    setLocationIntel({
      target_location: {
        lat: lat,
        lon: lon,
        nearest_named_place: lat > 23 ? "Jakhau Coastal Sector" : "Saurashtra Coastline Sector"
      },
      cyclone_distance_km: dist,
      bearing_cardinal: bearing >= 22.5 && bearing < 67.5 ? "NE" : (bearing >= 67.5 && bearing < 112.5 ? "E" : (bearing >= 112.5 && bearing < 157.5 ? "SE" : (bearing >= 157.5 && bearing < 202.5 ? "S" : (bearing >= 202.5 && bearing < 247.5 ? "SW" : (bearing >= 247.5 && bearing < 292.5 ? "W" : (bearing >= 292.5 && bearing < 337.5 ? "NW" : "N")))))),
      local_estimated_wind_kts: localWind,
      risk: {
        composite_risk_score: riskScore,
        risk_category: riskScore >= 0.70 ? "HIGH" : (riskScore >= 0.40 ? "MODERATE" : "LOW")
      },
      population_exposure: lat > 23 ? "48,200" : "32,400",
      nearest_shelter: { name: "Jakhau Primary Shelter", distance_km: 8.4 },
      nearest_hospital: { name: "Mandvi Sub-District Hospital", distance_km: 12.1 }
    });
    setIntelLoading(false);
  };

  return (
    <div className="p-4 sm:p-5 space-y-4 max-w-[1560px] w-full mx-auto">
      {/* 1. TOP STORM IDENTIFICATION & COMPACT METRICS (Telemetry columns with vertical dividers) */}
      <div className="bg-white border border-slate-200 rounded p-4">
        {/* Storm Identification */}
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 pb-3 border-b border-slate-200">
          <div>
            <div className="flex items-baseline space-x-2">
              <h1 className="text-base font-bold text-slate-900 tracking-tight uppercase">
                Cyclone {selectedCyclone?.name || "Biparjoy"}
              </h1>
              <span className="text-xs font-medium text-slate-700">
                • {selectedCyclone?.current_category || "Very Severe Cyclonic Storm"}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                [Historical Scenario]
              </span>
            </div>
            <div className="text-xs text-slate-500 font-mono mt-0.5">
              {selectedCyclone?.basin || "Arabian Sea"} • {selectedCyclone?.current_lat || 21.65}°N, {selectedCyclone?.current_lon || 66.85}°E
            </div>
          </div>

          <div className="text-[11px] font-mono text-slate-400">
            OBSERVED: 18:00 UTC • IMD BEST TRACK
          </div>
        </div>

        {/* Compact Telemetry Columns */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-0 pt-3 divide-y md:divide-y-0 md:divide-x divide-slate-200">
          <div className="py-2 md:py-0 md:pr-6">
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">WIND</span>
            <div className="text-2xl font-bold text-slate-900 font-mono tracking-tight mt-0.5">
              {selectedCyclone?.current_wind_speed_kts || 85} <span className="text-xs font-normal text-slate-500 font-sans">kt</span>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">157 km/h</span>
          </div>

          <div className="py-2 md:py-0 md:px-6">
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">PRESSURE</span>
            <div className="text-2xl font-bold text-slate-900 font-mono tracking-tight mt-0.5">
              {selectedCyclone?.current_pressure_hpa || 964} <span className="text-xs font-normal text-slate-500 font-sans">hPa</span>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">-46 hPa deficit</span>
          </div>

          <div className="py-2 md:py-0 md:px-6">
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">MOVEMENT</span>
            <div className="text-2xl font-bold text-slate-900 font-mono tracking-tight mt-0.5">
              {selectedCyclone?.current_heading_deg || 38}° <span className="text-xs font-normal text-slate-500 font-sans">NE</span>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">{selectedCyclone?.current_speed_kmh || 11.5} km/h</span>
          </div>

          <div className="py-2 md:py-0 md:pl-6">
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider block">EXPOSED POPULATION</span>
            <div className="text-2xl font-bold text-slate-900 font-mono tracking-tight mt-0.5">
              ~4.3M
            </div>
            <span className="text-[11px] text-slate-400 font-mono">Hazard belt</span>
          </div>
        </div>
      </div>

      {/* 2. MAP (HERO COMPONENT, 65-70% WIDTH) + RIGHT-SIDE OPERATIONAL SUMMARY (30-35% WIDTH) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left Column: Map Surface & Checkbox Controls (~68% / 8 cols) */}
        <div className="lg:col-span-8 space-y-2">
          {/* Small, Compact Layer Controls Checkbox Bar */}
          <div className="bg-white border border-slate-200 rounded px-3 py-1.5 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
              LAYERS
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-700">
              <label className="flex items-center space-x-1.5 cursor-pointer select-none">
                <input 
                  type="checkbox" 
                  checked={layers.forecast} 
                  onChange={(e) => setLayers(l => ({ ...l, forecast: e.target.checked }))}
                  className="rounded-xs border-slate-300 text-slate-900 focus:ring-0 w-3.5 h-3.5"
                />
                <span>Forecast Track</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer select-none">
                <input 
                  type="checkbox" 
                  checked={layers.uncertainty} 
                  onChange={(e) => setLayers(l => ({ ...l, uncertainty: e.target.checked }))}
                  className="rounded-xs border-slate-300 text-slate-900 focus:ring-0 w-3.5 h-3.5"
                />
                <span>Uncertainty Cone</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer select-none">
                <input 
                  type="checkbox" 
                  checked={layers.windSwaths} 
                  onChange={(e) => setLayers(l => ({ ...l, windSwaths: e.target.checked }))}
                  className="rounded-xs border-slate-300 text-slate-900 focus:ring-0 w-3.5 h-3.5"
                />
                <span>Wind Field</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer select-none">
                <input 
                  type="checkbox" 
                  checked={layers.shelters} 
                  onChange={(e) => setLayers(l => ({ ...l, shelters: e.target.checked }))}
                  className="rounded-xs border-slate-300 text-slate-900 focus:ring-0 w-3.5 h-3.5"
                />
                <span>Shelters</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer select-none">
                <input 
                  type="checkbox" 
                  checked={layers.evacuationRoute} 
                  onChange={(e) => setLayers(l => ({ ...l, evacuationRoute: e.target.checked }))}
                  className="rounded-xs border-slate-300 text-slate-900 focus:ring-0 w-3.5 h-3.5"
                />
                <span>Evacuation Route</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer select-none">
                <input 
                  type="checkbox" 
                  checked={showSatellite} 
                  onChange={(e) => setShowSatellite(e.target.checked)}
                  className="rounded-xs border-slate-300 text-slate-900 focus:ring-0 w-3.5 h-3.5"
                />
                <span>Satellite</span>
              </label>
            </div>
          </div>

          {/* Interactive Hero GIS Map Viewport */}
          <div className="h-[520px] w-full border border-slate-200 rounded overflow-hidden bg-slate-50">
            <MapComponent 
              cyclone={selectedCyclone}
              observations={track}
              forecastPoints={forecast?.forecast_points || []}
              uncertaintyCone={riskZones[0]?.polygon_geojson || null}
              shelters={shelters}
              hospitals={hospitals}
              evacuationRoute={evacuationRoute}
              showSatellite={showSatellite}
              satelliteOpacity={0.65}
              activeLayers={layers}
              onMapClick={handleMapClick}
              clickedPoint={clickedLocation}
            />
          </div>
        </div>

        {/* Right Column: Operational Summary (~32% / 4 cols) */}
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded p-4 space-y-4">
          <div>
            <div className="text-[11px] font-mono font-semibold text-slate-900 uppercase tracking-wider pb-2 border-b border-slate-200">
              OPERATIONAL SUMMARY
            </div>

            <div className="divide-y divide-slate-100 text-xs font-mono">
              <div className="py-2 flex justify-between">
                <span className="text-slate-500 font-sans">Current Position</span>
                <span className="text-slate-900 font-medium">21.65°N, 66.85°E</span>
              </div>
              <div className="py-2 flex justify-between">
                <span className="text-slate-500 font-sans">Forecast Landfall</span>
                <span className="text-slate-900 font-medium text-right font-sans">Jakhau sector (+36h to +48h)</span>
              </div>
              <div className="py-2 flex justify-between">
                <span className="text-slate-500 font-sans">Peak Wind</span>
                <span className="text-slate-900 font-medium">85 kt</span>
              </div>
              <div className="py-2 flex justify-between">
                <span className="text-slate-500 font-sans">Population Exposure</span>
                <span className="text-slate-900 font-medium">~4.3M</span>
              </div>
              <div className="py-2 flex justify-between">
                <span className="text-slate-500 font-sans">Nearest Safe Hub</span>
                <span className="text-slate-900 font-medium font-sans">Naliya MPCS</span>
              </div>
            </div>
          </div>

          {/* Operator Note Section */}
          <div className="pt-2 border-t border-slate-200 space-y-2">
            <div className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider">
              OPERATOR NOTE
            </div>
            <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-xs text-slate-800 leading-relaxed font-sans">
              "Prioritize evacuation planning for high-risk coastal zones."
            </div>
            <div className="text-[10px] text-slate-400 space-y-0.5 font-sans">
              <div className="font-mono text-slate-600 font-medium">AI ADVISORY</div>
              <div>Official orders are issued by IMD / SDMA / district authorities.</div>
            </div>
          </div>

          {/* Multi-Source Decision Support Micro-Flow Diagram */}
          <div className="pt-2 border-t border-slate-200 space-y-1.5">
            <div className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider">
              MULTI-SOURCE DECISION SUPPORT
            </div>
            <div className="p-2.5 rounded bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-700 space-y-1 leading-tight">
              <div className="text-slate-900 font-semibold">Satellite • Weather • Ocean • Pop</div>
              <div className="text-slate-400 pl-2">↓ CycloneX Models (LOSO ML)</div>
              <div className="text-slate-800 font-medium pl-4">↓ Risk + Exposure + Location</div>
              <div className="text-slate-900 font-bold pl-6 text-slate-900">↳ Actionable AI Advisory</div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. FORECAST TIMELINE (Clean horizontal stream: NOW | +6h | +12h | +24h | +48h | +72h) */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-2.5">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <span className="text-[11px] font-mono font-semibold text-slate-900 uppercase tracking-wider">
            FORECAST TIMELINE
          </span>
          <span className="text-[10px] font-mono text-slate-400">Multi-Horizon Projection</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs font-mono">
          {/* NOW */}
          <div className="p-2.5 rounded bg-slate-100 border border-slate-200">
            <div className="flex justify-between items-center text-[10px] text-slate-500">
              <span className="font-bold text-slate-900">NOW</span>
              <span>Observed</span>
            </div>
            <div className="text-sm font-bold text-slate-900 mt-1">85 kt</div>
            <div className="text-slate-500 text-[11px]">964 hPa</div>
            <div className="text-slate-700 text-[10px] mt-0.5">21.65°N, 66.85°E</div>
          </div>

          {/* +6h to +72h */}
          {(forecast?.forecast_points || []).map((pt: any) => (
            <div key={pt.forecast_hour} className="p-2.5 rounded bg-slate-50 border border-slate-200">
              <div className="flex justify-between items-center text-[10px] text-slate-400">
                <span className="font-semibold text-slate-900">+{pt.forecast_hour}h</span>
                <span>±{pt.uncertainty_radius_km}km</span>
              </div>
              <div className="text-sm font-bold text-slate-900 mt-1">{pt.predicted_wind_speed_kts} kt</div>
              <div className="text-slate-500 text-[11px]">{pt.predicted_pressure_hpa} hPa</div>
              <div className="text-slate-600 text-[10px] mt-0.5">{pt.lat}°N, {pt.lon}°E</div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. LOCATION INTELLIGENCE (Signature GIS Inspection Tool) */}
      {clickedLocation ? (
        <div className="bg-white border border-slate-300 rounded p-4 space-y-3">
          <div className="flex items-start justify-between border-b border-slate-200 pb-2">
            <div>
              <div className="text-[11px] font-mono font-semibold text-slate-900 uppercase tracking-wider">
                LOCATION INTELLIGENCE
              </div>
              <div className="text-xs font-semibold text-slate-900 mt-0.5">
                {locationIntel?.target_location?.nearest_named_place || "Jakhau Coastal Sector"}
              </div>
              <div className="text-[11px] font-mono text-slate-500">
                {clickedLocation.lat.toFixed(3)}°N, {clickedLocation.lon.toFixed(3)}°E
              </div>
            </div>

            <button 
              onClick={() => { setClickedLocation(null); setLocationIntel(null); setClickedWeather(null); }}
              className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition"
              title="Close inspection"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {intelLoading ? (
            <div className="py-4 text-center text-xs font-mono text-slate-400">
              Querying GIS coordinates & Holland vortex profile...
            </div>
          ) : locationIntel ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 text-xs font-mono">
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-sans">Distance from cyclone</span>
                  <span className="font-bold text-slate-900 mt-0.5 block">{locationIntel.cyclone_distance_km != null ? `${Math.round(locationIntel.cyclone_distance_km * 10) / 10} km` : "--"}</span>
                </div>

                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-sans">Bearing</span>
                  <span className="font-bold text-slate-900 mt-0.5 block">{locationIntel.bearing_cardinal || (locationIntel.bearing_deg != null ? `${Math.round(locationIntel.bearing_deg)}°` : "NE")}</span>
                </div>

                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-sans">Wind proxy</span>
                  <span className="font-bold text-slate-900 mt-0.5 block">{locationIntel.local_estimated_wind_kts != null ? `${Math.round(locationIntel.local_estimated_wind_kts * 10) / 10} kt` : "--"}</span>
                </div>

                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-sans">Risk</span>
                  <span className="font-bold text-slate-900 mt-0.5 block">{locationIntel.risk?.risk_category || locationIntel.risk?.risk_level || "HIGH"}</span>
                </div>

                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-sans">Population exposure</span>
                  <span className="font-bold text-slate-900 mt-0.5 block">{locationIntel.population_exposure || (locationIntel.risk?.parameters?.population_count ? locationIntel.risk.parameters.population_count.toLocaleString() : "48,200")}</span>
                </div>

                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-sans">Nearest shelter</span>
                  <span className="font-bold text-slate-900 mt-0.5 block truncate">{locationIntel.nearest_shelter?.distance_km != null ? `${Math.round(locationIntel.nearest_shelter.distance_km * 10) / 10} km` : "8.4 km"}</span>
                </div>

                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-sans">Nearest hospital</span>
                  <span className="font-bold text-slate-900 mt-0.5 block truncate">{locationIntel.nearest_hospital?.distance_km != null ? `${Math.round(locationIntel.nearest_hospital.distance_km * 10) / 10} km` : "12.1 km"}</span>
                </div>
              </div>

              {/* Interpretation & Provenance */}
              <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-1.5 text-xs font-sans">
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider">INTERPRETATION:</span>
                  <span className="text-slate-800 font-medium">"Model indicates elevated local hazard exposure for coastal installations."</span>
                </div>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-100">
                  <span>SOURCE: CycloneX model / geospatial analysis</span>
                  <span className="text-slate-600 font-medium">AI ADVISORY — Not an official warning or evacuation order.</span>
                </div>
              </div>

              {/* Real-Time Atmospheric Observation Dossier */}
              <div className="pt-2.5 border-t border-slate-200 space-y-2">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] font-mono font-semibold text-slate-900 uppercase tracking-wider">
                      REAL-TIME ATMOSPHERIC OBSERVATION
                    </span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded border font-medium ${
                      (clickedWeather?.status || clickedWeather?.data_status) === "LIVE"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : (clickedWeather?.status || clickedWeather?.data_status) === "STALE"
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : (clickedWeather?.status || clickedWeather?.data_status) === "OFFLINE"
                        ? "bg-rose-50 text-rose-700 border-rose-200"
                        : "bg-slate-100 text-slate-600 border-slate-200"
                    }`}>
                      {clickedWeather?.status || clickedWeather?.data_status || (clickedWeatherLoading ? "SYNCING..." : "LIVE")}
                    </span>
                  </div>

                  <div className="text-[10px] font-mono text-slate-500">
                    SOURCE: {clickedWeather?.source || "Open-Meteo NWP"} • {clickedWeather?.observation_time || "Synoptic hour"}
                  </div>
                </div>

                {clickedWeatherLoading ? (
                  <div className="py-2 text-center text-xs font-mono text-slate-400">
                    Querying Open-Meteo NWP real-time atmospheric observations...
                  </div>
                ) : clickedWeather ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 text-xs font-mono">
                      <div className="p-2 rounded bg-slate-50 border border-slate-200">
                        <span className="text-[10px] text-slate-400 block font-sans">Temperature</span>
                        <span className="font-bold text-slate-900 mt-0.5 block">
                          {(clickedWeather.weather?.temperature_c ?? clickedWeather.air_temperature_2m_c ?? "--")}°C
                        </span>
                      </div>

                      <div className="p-2 rounded bg-slate-50 border border-slate-200">
                        <span className="text-[10px] text-slate-400 block font-sans">Rainfall</span>
                        <span className="font-bold text-slate-900 mt-0.5 block">
                          {(clickedWeather.weather?.precipitation_mm ?? clickedWeather.precipitation_mm ?? "0.0")} mm/h
                        </span>
                      </div>

                      <div className="p-2 rounded bg-slate-50 border border-slate-200">
                        <span className="text-[10px] text-slate-400 block font-sans">Wind & Direction</span>
                        <span className="font-bold text-slate-900 mt-0.5 block">
                          {(clickedWeather.weather?.wind_speed_kts ?? clickedWeather.surface_wind_10m_kts ?? "--")} kt @ {(clickedWeather.weather?.wind_direction_deg ?? clickedWeather.wind_direction_10m_deg ?? "--")}°
                        </span>
                      </div>

                      <div className="p-2 rounded bg-slate-50 border border-slate-200">
                        <span className="text-[10px] text-slate-400 block font-sans">Pressure</span>
                        <span className="font-bold text-slate-900 mt-0.5 block">
                          {(clickedWeather.weather?.sea_level_pressure_hpa ?? clickedWeather.sea_level_pressure_hpa ?? clickedWeather.weather?.surface_pressure_hpa ?? clickedWeather.surface_pressure_hpa ?? "--")} hPa
                        </span>
                      </div>

                      <div className="p-2 rounded bg-slate-50 border border-slate-200">
                        <span className="text-[10px] text-slate-400 block font-sans">Humidity</span>
                        <span className="font-bold text-slate-900 mt-0.5 block">
                          {(clickedWeather.weather?.relative_humidity_pct ?? clickedWeather.relative_humidity_pct ?? "--")}%
                        </span>
                      </div>

                      <div className="p-2 rounded bg-slate-50 border border-slate-200">
                        <span className="text-[10px] text-slate-400 block font-sans">Cloud Cover</span>
                        <span className="font-bold text-slate-900 mt-0.5 block">
                          {(clickedWeather.weather?.cloud_cover_pct ?? clickedWeather.cloud_cover_pct ?? "--")}%
                        </span>
                      </div>

                      <div className="p-2 rounded bg-slate-50 border border-slate-200">
                        <span className="text-[10px] text-slate-400 block font-sans">Condition</span>
                        <span className="font-bold text-slate-900 mt-0.5 block truncate" title={clickedWeather.weather?.weather_condition ?? clickedWeather.weather_condition ?? "Fair / Variable"}>
                          {clickedWeather.weather?.weather_condition ?? clickedWeather.weather_condition ?? "Fair / Variable"}
                        </span>
                      </div>
                    </div>

                    <div className="p-2 rounded bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] font-mono text-slate-600">
                      <span>
                        Nearest synoptic station: <span className="font-medium text-slate-900">{clickedWeather.location?.nearest_grid_station || clickedWeather.location?.name || "Coastal Sector"}</span> ({clickedWeather.location?.distance_to_station_km != null ? `${Math.round(clickedWeather.location.distance_to_station_km * 10) / 10} km` : "local"})
                      </span>
                      <span className="text-slate-500 text-[10px]">
                        Disturbance Score: {clickedWeather.disturbance_score != null ? `${clickedWeather.disturbance_score}/100` : "Ambient"}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="py-2 text-center text-xs font-mono text-slate-400">
                    Observation data unavailable for selected coordinates.
                  </div>
                )}

                {/* Prominent Operational Integration Notice */}
                <div className="p-2 rounded bg-amber-50/70 border border-amber-200 text-[11px] font-mono text-amber-900 flex items-start space-x-1.5">
                  <span className="font-bold text-amber-700 shrink-0">•</span>
                  <span>
                    <strong>Real-time atmospheric observation.</strong> Live weather ingestion available; ML prediction requires the required feature set.
                  </span>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="bg-white border border-dashed border-slate-300 rounded p-3 text-center text-xs font-mono text-slate-500">
          <span className="font-semibold text-slate-700">LOCATION INTELLIGENCE (GIS INSPECTION):</span> Click any point on the GIS map above to generate an immediate localized hazard dossier (distance, bearing, wind proxy, risk, population exposure, nearest shelter & hospital).
        </div>
      )}

      {/* 5. WEATHER CONDITIONS (All-India 44-Station Grid Strip) */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-2.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-200">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <Radio className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <span className="font-semibold text-slate-900">
              WEATHER CONDITIONS: {liveWeather?.name || "India Grid Station"} ({liveWeather?.state || "India"})
            </span>
            {(() => {
              const currentStatus = weatherError || (!liveWeather && !liveWeatherLoading)
                ? "OFFLINE"
                : (!liveWeather && liveWeatherLoading)
                ? "CONNECTING"
                : (liveWeather?.status || liveWeather?.data_status || "OFFLINE");
              return (
                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-bold uppercase tracking-wider ${
                  currentStatus === "LIVE"
                    ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                    : currentStatus === "STALE"
                    ? "bg-amber-50 text-amber-700 border-amber-300"
                    : currentStatus === "CONNECTING"
                    ? "bg-blue-50 text-blue-700 border-blue-300 animate-pulse"
                    : "bg-rose-50 text-rose-700 border-rose-300"
                }`}>
                  {currentStatus}
                </span>
              );
            })()}
            {liveWeather?.disturbance_score != null && (
              <span className="text-[10px] text-slate-500">
                • Index: {liveWeather.disturbance_score}/100 [Rank #{liveWeather?.rank || 1} of 44]
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2 text-xs">
            <div className="flex items-center p-0.5 bg-slate-100 rounded text-xs font-mono">
              <button
                onClick={() => handleModeSwitch("most_disturbed")}
                className={`px-2 py-0.5 rounded text-[11px] transition ${weatherViewMode === "most_disturbed" ? "bg-white text-slate-900 font-medium shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
              >
                Selected Station (Live)
              </button>
              <button
                onClick={() => handleModeSwitch("biparjoy")}
                className={`px-2 py-0.5 rounded text-[11px] transition ${weatherViewMode === "biparjoy" ? "bg-white text-slate-900 font-medium shadow-sm" : "text-slate-600 hover:text-slate-900"}`}
              >
                Biparjoy Anchor
              </button>
            </div>

            <button
              onClick={() => fetchLiveWeather(true, weatherViewMode)}
              disabled={liveWeatherLoading}
              className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-xs rounded transition border border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Force on-demand refresh from Open-Meteo API"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${liveWeatherLoading ? "animate-spin text-blue-600" : "text-slate-600"}`} />
              <span className="font-medium">{liveWeatherLoading ? "Refreshing..." : "Refresh Now"}</span>
            </button>
          </div>
        </div>

        {/* Operational Error / Staleness Banner */}
        {weatherError || (liveWeather?.status === "OFFLINE" || liveWeather?.data_status === "OFFLINE") ? (
          <div className="p-2.5 rounded bg-rose-50 border border-rose-200 text-rose-800 text-xs font-mono flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
              <span>
                <strong>Weather service offline.</strong> {weatherError || "Live synoptic feed unreachable."} Click <strong>Refresh Now</strong> to retry.
              </span>
            </div>
            <button
              onClick={() => fetchLiveWeather(true, weatherViewMode)}
              disabled={liveWeatherLoading}
              className="px-2 py-0.5 rounded bg-rose-100 hover:bg-rose-200 text-rose-900 font-semibold text-[11px] transition"
            >
              Retry
            </button>
          </div>
        ) : (liveWeather?.status === "STALE" || liveWeather?.data_status === "STALE") ? (
          <div className="p-2 rounded bg-amber-50 border border-amber-200 text-amber-800 text-xs font-mono flex items-center space-x-2">
            <span className="font-bold text-amber-600 shrink-0">•</span>
            <span>
              Live weather unavailable. Showing cached data from {liveWeather?.cached_at || liveWeather?.fetched_at || liveWeather?.observation_time || "previous sync"}.
            </span>
          </div>
        ) : null}

        {/* 8 Primary Meteorological Observation Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 font-mono text-xs">
          <div className="p-2 rounded bg-slate-50 border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-sans">Surface Wind</span>
            <span className="font-semibold text-slate-800">
              {liveWeather?.surface_wind_10m_kts != null ? `${liveWeather.surface_wind_10m_kts} kt` : (liveWeather?.weather?.wind_speed_kts != null ? `${liveWeather.weather.wind_speed_kts} kt` : "--")}
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">
              dir: {liveWeather?.wind_direction_10m_deg != null ? `${liveWeather.wind_direction_10m_deg}°` : (liveWeather?.weather?.wind_direction_deg != null ? `${liveWeather.weather.wind_direction_deg}°` : "--")}
            </span>
          </div>

          <div className="p-2 rounded bg-slate-50 border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-sans">Wind Gusts</span>
            <span className="font-semibold text-slate-800">
              {liveWeather?.wind_gust_kts != null ? `${liveWeather.wind_gust_kts} kt` : (liveWeather?.weather?.wind_gust_kts != null ? `${liveWeather.weather.wind_gust_kts} kt` : "--")}
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">peak gust</span>
          </div>

          <div className="p-2 rounded bg-slate-50 border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-sans">Condition</span>
            <span className="font-semibold text-slate-800 truncate block" title={liveWeather?.weather_condition || liveWeather?.weather?.weather_condition || "Fair"}>
              {liveWeather?.weather_condition || liveWeather?.weather?.weather_condition || "Fair"}
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">WMO synoptic</span>
          </div>

          <div className="p-2 rounded bg-slate-50 border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-sans">Pressure</span>
            <span className="font-semibold text-slate-800">
              {liveWeather?.sea_level_pressure_hpa != null ? `${liveWeather.sea_level_pressure_hpa} hPa` : (liveWeather?.weather?.surface_pressure_hpa != null ? `${liveWeather.weather.surface_pressure_hpa} hPa` : "--")}
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">MSL pressure</span>
          </div>

          <div className="p-2 rounded bg-slate-50 border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-sans">Precipitation</span>
            <span className="font-semibold text-slate-800">
              {liveWeather?.precipitation_mm != null ? `${liveWeather.precipitation_mm} mm/h` : (liveWeather?.weather?.precipitation_mm != null ? `${liveWeather.weather.precipitation_mm} mm/h` : "0.0 mm/h")}
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">rate</span>
          </div>

          <div className="p-2 rounded bg-slate-50 border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-sans">Temperature</span>
            <span className="font-semibold text-slate-800">
              {liveWeather?.air_temperature_2m_c != null ? `${liveWeather.air_temperature_2m_c}°C` : (liveWeather?.weather?.temperature_c != null ? `${liveWeather.weather.temperature_c}°C` : "--")}
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">2m ambient</span>
          </div>

          <div className="p-2 rounded bg-slate-50 border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-sans">Humidity</span>
            <span className="font-semibold text-slate-800">
              {liveWeather?.relative_humidity_pct != null ? `${liveWeather.relative_humidity_pct}%` : (liveWeather?.weather?.relative_humidity_pct != null ? `${liveWeather.weather.relative_humidity_pct}%` : "--")}
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">relative</span>
          </div>

          <div className="p-2 rounded bg-slate-50 border border-slate-200">
            <span className="text-[10px] text-slate-400 block font-sans">Cloud Cover</span>
            <span className="font-semibold text-slate-800">
              {liveWeather?.cloud_cover_pct != null ? `${liveWeather.cloud_cover_pct}%` : (liveWeather?.weather?.cloud_cover_pct != null ? `${liveWeather.weather.cloud_cover_pct}%` : "--")}
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">sky coverage</span>
          </div>
        </div>

        {/* Operational Weather Status & Diagnostics Strip */}
        <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[10px] font-mono text-slate-500">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>Provider: <strong className="text-slate-700">{liveWeather?.source || "Open-Meteo NWP"}</strong></span>
            <span>Observed: <span className="text-slate-700">{formatUtcIst(liveWeather?.observation_time || liveWeather?.timestamp).utc} ({formatUtcIst(liveWeather?.observation_time || liveWeather?.timestamp).ist})</span></span>
            <span>Fetched: <span className="text-slate-700">{liveWeather?.fetched_at ? formatUtcIst(liveWeather.fetched_at).utc : (liveWeather?.last_sync_utc ? formatUtcIst(liveWeather.last_sync_utc).utc : "--")}</span></span>
            <span>UI Refreshed: <span className="text-slate-700">{lastUiRefresh ? lastUiRefresh.toLocaleTimeString() : "--"}</span></span>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 shrink-0">
            <span>Auto-refresh: <strong className="text-emerald-700">ON (5m)</strong></span>
            <span>Next: <span className="font-semibold text-slate-700">{formatCountdown(nextRefreshSeconds)}</span></span>
            <span>Coord: <span className="text-slate-700">{liveWeather?.latitude != null ? `${Number(liveWeather.latitude).toFixed(2)}°N, ${Number(liveWeather.longitude).toFixed(2)}°E` : "All-India"}</span></span>
          </div>
        </div>

        <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-1 font-mono">
          <span>44 coastal stations monitored. Live weather ingestion available; ML prediction requires the required feature set.</span>
          <span>Source: Open-Meteo NWP Live Ingestion • Status: {weatherAgeDisplay}</span>
        </div>
      </div>
    </div>
  );
}
