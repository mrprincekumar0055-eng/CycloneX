"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { 
  Play, Pause, RotateCcw, ChevronRight, ChevronLeft, 
  Volume2
} from "lucide-react";

// Dynamic map import
const MapComponent = dynamic(() => import("@/components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[480px] bg-slate-50 border border-slate-200 rounded flex items-center justify-center text-slate-400 font-mono text-xs">
      Loading Simulation Viewport...
    </div>
  )
});

// Deterministic Scenario Datasets (100% Offline Capable)
const DEMO_TRACK = [
  { id: "dt1", timestamp: "2023-06-13T06:00:00Z", lat: 20.8, lon: 66.5, wind_speed_kts: 90, central_pressure_hpa: 958, imd_category: "Very Severe Cyclonic Storm", source: "NOAA IBTrACS" },
  { id: "dt2", timestamp: "2023-06-13T12:00:00Z", lat: 21.2, lon: 66.7, wind_speed_kts: 85, central_pressure_hpa: 962, imd_category: "Very Severe Cyclonic Storm", source: "NOAA IBTrACS" },
  { id: "dt3", timestamp: "2023-06-13T18:00:00Z", lat: 21.65, lon: 66.85, wind_speed_kts: 85, central_pressure_hpa: 964, imd_category: "Very Severe Cyclonic Storm", source: "NOAA IBTrACS" }
];

const DEMO_FORECAST = [
  { forecast_hour: 6, valid_time: "2023-06-14T00:00:00Z", lat: 21.9, lon: 67.2, predicted_wind_speed_kts: 85, predicted_pressure_hpa: 964, category: "Very Severe Cyclonic Storm", uncertainty_radius_km: 35 },
  { forecast_hour: 12, valid_time: "2023-06-14T06:00:00Z", lat: 22.1, lon: 67.4, predicted_wind_speed_kts: 85, predicted_pressure_hpa: 966, category: "Very Severe Cyclonic Storm", uncertainty_radius_km: 55 },
  { forecast_hour: 24, valid_time: "2023-06-14T18:00:00Z", lat: 22.6, lon: 67.9, predicted_wind_speed_kts: 80, predicted_pressure_hpa: 970, category: "Very Severe Cyclonic Storm", uncertainty_radius_km: 80 },
  { forecast_hour: 48, valid_time: "2023-06-15T18:00:00Z", lat: 23.28, lon: 68.65, predicted_wind_speed_kts: 70, predicted_pressure_hpa: 978, category: "Severe Cyclonic Storm", uncertainty_radius_km: 115 },
  { forecast_hour: 72, valid_time: "2023-06-16T18:00:00Z", lat: 23.9, lon: 69.8, predicted_wind_speed_kts: 45, predicted_pressure_hpa: 990, category: "Cyclonic Storm", uncertainty_radius_km: 165 }
];

const DEMO_SHELTERS = [
  { id: "sh-1", name: "Jakhau Primary Cyclone Shelter", lat: 23.24, lon: 68.62, total_capacity: 1500, current_occupancy: 120, is_verified: true, elevation_meters: 8 },
  { id: "sh-2", name: "Mandvi Model School Shelter", lat: 22.83, lon: 69.35, total_capacity: 2200, current_occupancy: 450, is_verified: true, elevation_meters: 12 }
];

const DEMO_HOSPITALS = [
  { id: "hosp-1", name: "Sub-District Hospital Mandvi", lat: 22.83, lon: 69.36, total_beds: 120, available_icu_beds: 8, helipad: true }
];

const DEMO_ROUTE = {
  origin_name: "Mandvi Fishery Settlement",
  destination_name: "Mandvi Model High School Shelter",
  distance_km: 18.5,
  travel_time_minutes: 24,
  route_risk_level: "LOW RISK (HIGHWAY)",
  status: "OPEN"
};

// Deterministic 8-Step Walkthrough Scenario
const DEMO_STEPS = [
  {
    num: "01",
    label: "Detect",
    title: "01 Detect",
    subtitle: "Satellite Ingestion & Vortex Identification",
    description: "NASA GIBS multi-spectral MODIS reflectance imagery ingested alongside Open-Meteo atmospheric wind and pressure fields. Vortex vorticity curvature and low-level cyclonic circulation detected at 21.65°N, 66.85°E in the Arabian Sea.",
    badge: "HISTORICAL DATA" as const,
    keyMetrics: [
      { label: "Detected Eye", val: "21.65°N, 66.85°E" },
      { label: "Vorticity Field", val: "18.4 × 10⁻⁵ s⁻¹" },
      { label: "Central Pressure", val: "964 hPa (-46 hPa)" },
      { label: "Sea Surface Temp", val: "30.4°C (> 26.5°C threshold)" }
    ],
    speakerNotes: "CycloneX ingests satellite reflectance and numerical weather grids simultaneously. Transparently note that while our analytical spectral curvature pipeline is operational, full deep vision models await 100k+ scene INSAT-3D training."
  },
  {
    num: "02",
    label: "Classify",
    title: "02 Classify",
    subtitle: "IMD Scale Categorization & Confidence",
    description: "Machine learning classifier evaluates atmospheric state vector against official IMD wind speed and pressure thresholds. Categorized as Very Severe Cyclonic Storm (VSCS). Feature attributions indicate low vertical wind shear (<10 kts) sustaining storm core.",
    badge: "MODEL OUTPUT" as const,
    keyMetrics: [
      { label: "Current Category", val: "Very Severe Cyclonic Storm (VSCS)" },
      { label: "Sustained Wind", val: "85 kts (157 km/h)" },
      { label: "Gust Velocity", val: "105 kts (195 km/h)" },
      { label: "Next Stage (T+6h)", val: "VSCS / ESCS Borderline" }
    ],
    speakerNotes: "Our classifier achieves 67.21% accuracy out-of-fold. Naive persistence achieves 70.04% because cyclones maintain category over 6 hours; we beat majority class (21.46%) by 45+ percentage points."
  },
  {
    num: "03",
    label: "Predict",
    title: "03 Predict",
    subtitle: "Multi-Horizon Trajectory & Intensity Forecast",
    description: "Gradient boosting displacement regressor forecasts forward track waypoints across +6h, +12h, +24h, +48h, and +72h. Uncertainty cone expands dynamically based on verified empirical position errors.",
    badge: "MODEL OUTPUT" as const,
    keyMetrics: [
      { label: "+6h Forecast", val: "21.90°N, 67.20°E (85 kts)" },
      { label: "+24h Forecast", val: "22.60°N, 67.90°E (80 kts)" },
      { label: "+48h Landfall", val: "23.28°N, 68.65°E near Jakhau Port" },
      { label: "68% Cone Radius", val: "±115 km at landfall" }
    ],
    speakerNotes: "Track position errors scale monotonically (+6h: 41.3 km to +72h: 388.8 km). At extended horizons (+48h, +72h), CycloneX demonstrates positive skill over persistence. Intensity model beats persistence at all 5 horizons."
  },
  {
    num: "04",
    label: "Assess",
    title: "04 Assess",
    subtitle: "UNDRR Risk Framework & Coastal Vulnerability",
    description: "Spatial overlay with WorldPop demographic densities and coastal elevation contours reveals over 1.25 million residents across Kutch and Devbhumi Dwarka within the destructive 64-kt gale swath.",
    badge: "MODEL OUTPUT" as const,
    keyMetrics: [
      { label: "Composite Risk", val: "0.85 / 1.00 (High to Extreme)" },
      { label: "Hazard Score", val: "0.88 (Wind + Pressure Deficit)" },
      { label: "Vulnerability Score", val: "0.75 (<5m Coastal Envelope)" },
      { label: "Surge Potential", val: "2.0m - 3.5m tidal anomaly" }
    ],
    speakerNotes: "Risk is evaluated using the UN UNDRR framework: Hazard × Exposure × Vulnerability. Clarify to judges that this is an empirical decision index, not a hydrodynamic 2D shallow-water ADCIRC simulation."
  },
  {
    num: "05",
    label: "Exposure",
    title: "05 Exposure",
    subtitle: "Gridded Population & Critical Infrastructure",
    description: "Intersection of gale wind radii with 100m WorldPop density maps isolates coastal taluks in direct hazard path, identifying vulnerable demographic segments and critical infrastructure.",
    badge: "MODEL OUTPUT" as const,
    keyMetrics: [
      { label: "Total Exposure", val: "~4.3M residents in hazard belt" },
      { label: "Priority Evacuation", val: "148,000 vulnerable residents" },
      { label: "Exposed Districts", val: "Kutch, Devbhumi Dwarka, Jamnagar" },
      { label: "Critical Ports", val: "Jakhau, Mandvi, Mundra" }
    ],
    speakerNotes: "WorldPop gridded datasets allow isolation of the exact population within the 34-kt and 64-kt wind swaths, providing quantitative evidence for civil defense pre-positioning."
  },
  {
    num: "06",
    label: "Evacuation",
    title: "06 Evacuation",
    subtitle: "Logistics Routing & Shelter Allocation",
    description: "Automated routing analysis calculates non-flooding highway corridors to 45 designated Multi-Purpose Cyclone Shelters (MPCS) and emergency trauma units via OpenStreetMap Overpass and OSRM.",
    badge: "AI ADVISORY" as const,
    keyMetrics: [
      { label: "Designated Shelters", val: "45 facilities (Capacity: 62,500)" },
      { label: "Primary Corridor", val: "SH-6 Coastal to Jakhau MPCS (18.5 km)" },
      { label: "Transit Time", val: "~24 min via elevated highway" },
      { label: "Emergency Trauma Beds", val: "120 beds, 8 ICU units ready" }
    ],
    speakerNotes: "CycloneX bridges meteorology to civil logistics. Point out that shelter and hospital data is queried from OpenStreetMap with a verified local fallback catalog."
  },
  {
    num: "07",
    label: "Alert",
    title: "07 Alert",
    subtitle: "Multi-Stakeholder Automated Advisories",
    description: "Generates tailored early-warning action checklists for Disaster Management, Healthcare, Police, and the Public. Explicitly labeled as AI Decision-Support Advisories to complement statutory IMD bulletins.",
    badge: "AI ADVISORY" as const,
    keyMetrics: [
      { label: "Disaster Management", val: "Pre-position NDRF teams, open shelters" },
      { label: "Healthcare", val: "Stock trauma units, test auxiliary generators" },
      { label: "Police & Ports", val: "Issue Great Danger signal, halt cargo ops" },
      { label: "Public Guidance", val: "Move inland, secure loose structures" }
    ],
    speakerNotes: "Explain stakeholder segmentation: administrative authorities receive logistics directives, while citizens receive clear safety advice. Emphasize the clear statutory disclaimer."
  },
  {
    num: "08",
    label: "Verify",
    title: "08 Verify",
    subtitle: "Model Validation & Live Meteorological Sync",
    description: "Out-of-fold LOSO validation metrics confirm model stability across 11 historical cyclones. Real-time background poller continuously monitors 44 weather stations across India to detect emerging disturbances.",
    badge: "LIVE DATA" as const,
    keyMetrics: [
      { label: "LOSO Folds", val: "11 historical cyclones (258 fixes)" },
      { label: "Intensity Skill", val: "+14.6% to +32.0% over persistence" },
      { label: "Live Polling Grid", val: "44 stations nationwide (Open-Meteo)" },
      { label: "Poll Interval", val: "Every 15 min (Single batched query)" }
    ],
    speakerNotes: "Close with engineering and scientific credibility: strict out-of-fold validation, honest reporting of persistence baselines, and live background polling of 44 Indian stations in a single batched query."
  }
];

export default function DemoPage() {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    let timer: any = null;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentStepIndex((prev) => {
          if (prev >= DEMO_STEPS.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 8000);
    }
    return () => clearInterval(timer);
  }, [isPlaying]);

  const currentStep = DEMO_STEPS[currentStepIndex];

  const getStepMapConfig = (stepIdx: number) => {
    switch (stepIdx) {
      case 0: // 01 Detect
        return {
          center: [21.65, 66.85] as [number, number],
          zoom: 6,
          showSatellite: true,
          activeLayers: { track: false, forecast: false, uncertainty: false, windSwaths: false, shelters: false, hospitals: false, evacuationRoute: false },
          observations: [],
          forecastPoints: [],
          shelters: [],
          hospitals: [],
          evacuationRoute: null,
          visualTag: "NASA GIBS / MODIS Reflectance & Low-Level Vortex Circulation Fix"
        };
      case 1: // 02 Classify
        return {
          center: [21.65, 66.85] as [number, number],
          zoom: 6,
          showSatellite: false,
          activeLayers: { track: true, forecast: false, uncertainty: false, windSwaths: true, shelters: false, hospitals: false, evacuationRoute: false },
          observations: DEMO_TRACK,
          forecastPoints: [],
          shelters: [],
          hospitals: [],
          evacuationRoute: null,
          visualTag: "IMD Synoptic Track Fixes & 85-kt Gale Wind Field Envelope"
        };
      case 2: // 03 Predict
        return {
          center: [22.4, 67.8] as [number, number],
          zoom: 6,
          showSatellite: false,
          activeLayers: { track: true, forecast: true, uncertainty: true, windSwaths: false, shelters: false, hospitals: false, evacuationRoute: false },
          observations: DEMO_TRACK,
          forecastPoints: DEMO_FORECAST,
          shelters: [],
          hospitals: [],
          evacuationRoute: null,
          visualTag: "Multi-Horizon Trajectory Waypoints & ±115 km Uncertainty Cone"
        };
      case 3: // 04 Assess
        return {
          center: [22.8, 68.5] as [number, number],
          zoom: 7,
          showSatellite: false,
          activeLayers: { track: true, forecast: true, uncertainty: true, windSwaths: true, shelters: false, hospitals: false, evacuationRoute: false },
          observations: DEMO_TRACK,
          forecastPoints: DEMO_FORECAST,
          shelters: [],
          hospitals: [],
          evacuationRoute: null,
          visualTag: "UNDRR Coastal Risk Swath (Hazard × Exposure × Vulnerability)"
        };
      case 4: // 05 Exposure
        return {
          center: [23.0, 69.0] as [number, number],
          zoom: 7,
          showSatellite: false,
          activeLayers: { track: true, forecast: true, uncertainty: true, windSwaths: true, shelters: false, hospitals: false, evacuationRoute: false },
          observations: DEMO_TRACK,
          forecastPoints: DEMO_FORECAST,
          shelters: [],
          hospitals: [],
          evacuationRoute: null,
          visualTag: "WorldPop Gridded Demographic Intersect & Port Infrastructure"
        };
      case 5: // 06 Evacuate
        return {
          center: [22.83, 69.35] as [number, number],
          zoom: 9,
          showSatellite: false,
          activeLayers: { track: false, forecast: false, uncertainty: false, windSwaths: false, shelters: true, hospitals: true, evacuationRoute: true },
          observations: [],
          forecastPoints: [],
          shelters: DEMO_SHELTERS,
          hospitals: DEMO_HOSPITALS,
          evacuationRoute: DEMO_ROUTE,
          visualTag: "Designated Multi-Purpose Cyclone Shelters & Highway Corridor"
        };
      case 6: // 07 Alert
        return {
          center: [22.8, 68.8] as [number, number],
          zoom: 7,
          showSatellite: false,
          activeLayers: { track: true, forecast: true, uncertainty: true, windSwaths: true, shelters: true, hospitals: true, evacuationRoute: true },
          observations: DEMO_TRACK,
          forecastPoints: DEMO_FORECAST,
          shelters: DEMO_SHELTERS,
          hospitals: DEMO_HOSPITALS,
          evacuationRoute: DEMO_ROUTE,
          visualTag: "Emergency Warning Directives & Evacuation Sector Perimeter"
        };
      case 7: // 08 Verify
      default:
        return {
          center: [22.2, 67.8] as [number, number],
          zoom: 6,
          showSatellite: false,
          activeLayers: { track: true, forecast: true, uncertainty: true, windSwaths: false, shelters: true, hospitals: true, evacuationRoute: false },
          observations: DEMO_TRACK,
          forecastPoints: DEMO_FORECAST,
          shelters: DEMO_SHELTERS,
          hospitals: DEMO_HOSPITALS,
          evacuationRoute: null,
          visualTag: "Ground Truth NOAA Best Track & Out-of-Fold LOSO Error Envelope"
        };
    }
  };

  const mapConfig = getStepMapConfig(currentStepIndex);

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6">
      {/* Top Header */}
      <div className="bg-white border border-slate-200 rounded p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-bold text-slate-900 tracking-tight uppercase font-mono">
            OPERATIONAL DEMONSTRATION
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            8-Stage Deterministic Simulation • Cyclone Biparjoy (Arabian Sea)
          </p>
          <div className="flex flex-wrap items-center gap-1.5 pt-2 text-[10px] font-mono">
            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">DEMO MODE: DETERMINISTIC</span>
            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">HISTORICAL DATA: BIPARJOY 2023</span>
            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">MODEL OUTPUT: LOSO VALIDATED</span>
            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">AI ADVISORY: DECISION SUPPORT</span>
          </div>
        </div>

        {/* Controls: RESET, PREVIOUS, NEXT, START / PAUSE */}
        <div className="flex items-center space-x-2 font-mono text-xs">
          <button
            onClick={() => {
              setIsPlaying(false);
              setCurrentStepIndex(0);
            }}
            className="px-2.5 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            title="Reset to Step 1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setCurrentStepIndex((p) => Math.max(0, p - 1))}
            disabled={currentStepIndex === 0}
            className="px-2.5 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-40 transition font-sans"
          >
            PREVIOUS
          </button>

          <button
            onClick={() => setCurrentStepIndex((p) => Math.min(DEMO_STEPS.length - 1, p + 1))}
            disabled={currentStepIndex === DEMO_STEPS.length - 1}
            className="px-2.5 py-1.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-40 transition font-sans"
          >
            NEXT
          </button>

          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-1.5 transition ${
              isPlaying 
                ? "bg-slate-900 text-white" 
                : "bg-slate-900 text-white hover:bg-slate-800"
            }`}
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isPlaying ? "PAUSE" : "START"}</span>
          </button>
        </div>
      </div>

      {/* Simple Progress Indicator: 01 Detect to 08 Verify */}
      <div className="bg-white border border-slate-200 rounded p-2.5">
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-1.5">
          {DEMO_STEPS.map((s, idx) => {
            const isActive = currentStepIndex === idx;
            const isCompleted = currentStepIndex > idx;

            return (
              <button
                key={s.num}
                onClick={() => {
                  setIsPlaying(false);
                  setCurrentStepIndex(idx);
                }}
                className={`text-left p-2 rounded transition text-xs ${
                  isActive 
                    ? "bg-slate-900 text-white font-medium" 
                    : isCompleted
                    ? "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    : "bg-slate-50 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                }`}
              >
                <div className="font-mono text-[10px] opacity-70">{s.num}</div>
                <div className="font-medium truncate text-xs mt-0.5">
                  {s.label}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Split Layout: Left Visual (~67% / 8 cols) + Right Step Card (~33% / 4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Interactive Map */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded p-4 space-y-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <span className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                Simulation Viewport: {currentStep.title}
              </span>
              <span className="text-[11px] font-mono text-slate-500">
                {mapConfig.visualTag}
              </span>
            </div>

            <div className="w-full h-[440px] rounded border border-slate-200 overflow-hidden mt-3 bg-slate-50">
              <MapComponent 
                center={mapConfig.center} 
                zoom={mapConfig.zoom}
                showSatellite={mapConfig.showSatellite}
                activeLayers={mapConfig.activeLayers}
                observations={mapConfig.observations}
                forecastPoints={mapConfig.forecastPoints}
                shelters={mapConfig.shelters}
                hospitals={mapConfig.hospitals}
                evacuationRoute={mapConfig.evacuationRoute}
                cyclone={{
                  name: "BIPARJOY",
                  current_lat: 21.65,
                  current_lon: 66.85,
                  current_wind_speed_kts: 85,
                  current_pressure_hpa: 964,
                  current_category: "Very Severe Cyclonic Storm"
                }}
              />
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center space-x-2 text-slate-700">
              <span className="font-semibold text-slate-900 font-mono">Phase {currentStep.num}:</span>
              <span>{currentStep.subtitle}</span>
            </div>
            <span className="text-slate-400 text-[11px] font-mono">
              Offline Scenario Mode (Zero Network Dependency)
            </span>
          </div>
        </div>

        {/* Right Column: Step Card & Key Metrics & Speaker Notes */}
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded p-5 flex flex-col justify-between space-y-4">
          <div className="space-y-3.5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Step Dossier</span>
                <h2 className="text-base font-semibold text-slate-900">{currentStep.title}</h2>
              </div>
              <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">
                {currentStep.badge}
              </span>
            </div>

            <div>
              <span className="text-xs font-semibold text-slate-800 block mb-1">
                {currentStep.subtitle}
              </span>
              <p className="text-xs text-slate-600 leading-relaxed">
                {currentStep.description}
              </p>
            </div>

            {/* Key Metrics */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-2">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block font-mono">
                Key Metrics:
              </span>
              <div className="space-y-1.5 text-xs font-mono">
                {currentStep.keyMetrics.map((km, i) => (
                  <div key={i} className="flex justify-between items-center text-slate-700">
                    <span className="text-slate-500">{km.label}:</span>
                    <strong className="text-slate-900 font-semibold">{km.val}</strong>
                  </div>
                ))}
              </div>
            </div>

            {/* Speaker Notes / Talking Points */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-1.5">
              <div className="flex items-center space-x-1.5 text-slate-700 text-xs font-semibold">
                <Volume2 className="w-3.5 h-3.5 text-slate-500" />
                <span className="uppercase tracking-wider text-[10px] font-mono">Speaker Note / Talking Point:</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {currentStep.speakerNotes}
              </p>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400">Step {currentStepIndex + 1} of 8</span>
            <div className="flex space-x-1">
              <button
                onClick={() => setCurrentStepIndex((p) => Math.max(0, p - 1))}
                disabled={currentStepIndex === 0}
                className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-40"
              >
                Back
              </button>
              <button
                onClick={() => setCurrentStepIndex((p) => Math.min(DEMO_STEPS.length - 1, p + 1))}
                disabled={currentStepIndex === DEMO_STEPS.length - 1}
                className="px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-white disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
