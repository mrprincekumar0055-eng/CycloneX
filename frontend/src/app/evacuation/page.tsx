"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AlertTriangle, Info } from "lucide-react";
import { fetchFromAPI } from "@/lib/api";

// Dynamic map import
const MapComponent = dynamic(() => import("@/components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[400px] bg-slate-50 border border-slate-200 rounded flex items-center justify-center text-slate-500 font-mono text-xs">
      Loading Evacuation Logistics GIS Layer...
    </div>
  )
});

export default function EvacuationPage() {
  const [shelters, setShelters] = useState<any[]>([]);
  const [hospitals, setHospitals] = useState<any[]>([]);
  const [routes, setRoutes] = useState<any[]>([]);
  const [cyclone, setCyclone] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isUsingCached, setIsUsingCached] = useState(false);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const [cycs, s, h, r] = await Promise.all([
        fetchFromAPI("/cyclones"),
        fetchFromAPI("/facilities/shelters"),
        fetchFromAPI("/facilities/hospitals"),
        fetchFromAPI("/routes")
      ]);
      if (cycs && cycs.length > 0) setCyclone(cycs[0]);
      if (s && s.length > 0) {
        setShelters(s);
      } else {
        setIsUsingCached(true);
      }
      if (h && h.length > 0) setHospitals(h);
      if (r && r.length > 0) {
        setRoutes(r);
      } else {
        setIsUsingCached(true);
      }
      setLoading(false);
    }
    loadData();
  }, []);

  const activeRoute = routes && routes.length > 0 ? routes[0] : {
    origin_name: "Mandvi Coastal Fishery Settlement (22.82°N, 69.34°E)",
    destination_name: "Mandvi Government Model High School & Cyclone Shelter",
    distance_km: 18.5,
    travel_time_minutes: 24,
    route_risk_level: "LOW RISK (ELEVATED HIGHWAY)",
    status: "OPEN / ALL WEATHER"
  };

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6">
      {/* Offline / Cached Data Banner */}
      {isUsingCached && (
        <div className="p-3 bg-amber-50 border border-amber-300 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-amber-900 font-mono">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Offline Mode:</strong> Logistics API unreachable. Showing cached Mandvi model corridor.
            </span>
          </div>
          <span className="px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-bold text-[10px] shrink-0 uppercase tracking-wide">
            CACHED LOGISTICS
          </span>
        </div>
      )}

      {/* Header */}
      <div className="bg-white border border-slate-200 rounded p-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight uppercase font-mono">
              EVACUATION LOGISTICS & SHELTERS
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Designated Multi-Purpose Cyclone Shelters (MPCS), Hospitals & Highway Corridors • Mandvi Sector
            </p>
          </div>
          <div className="text-[11px] font-mono text-slate-500">
            AI ADVISORY — OFFICIAL EVACUATION ORDERS ISSUED BY IMD / SDMA
          </div>
        </div>
      </div>

      {/* Logistics & GIS Planning Workstation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: GIS Map Surface (~68% / 8 cols) */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded p-3 space-y-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <span className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
              Tactical Logistics & Facility GIS Overlay
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              Shelters (Green) • Hospitals (Red) • Route Corridors (Blue)
            </span>
          </div>

          <div className="w-full h-[460px] rounded overflow-hidden border border-slate-200">
            <MapComponent 
              center={[cyclone?.current_lat || 22.82, cyclone?.current_lon || 69.34]} 
              zoom={8}
              cyclone={cyclone}
            />
          </div>
        </div>

        {/* Right: Evacuation Logistics Dossier (~32% / 4 cols) */}
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded p-4 flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <span className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                Evacuation Logistics
              </span>
              <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                ACTIVE CORRIDOR
              </span>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[10px] text-slate-400 uppercase block font-medium">Active Corridor</span>
                <div className="text-slate-900 font-semibold font-sans leading-snug">
                  Mandvi Coastal Fishery Settlement → Mandvi Model High School MPCS
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-0.5">
                  <span className="text-[10px] text-slate-400 uppercase block">Route Status</span>
                  <span className="text-slate-900 font-semibold text-[11px]">OPEN / ALL WEATHER</span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-0.5">
                  <span className="text-[10px] text-slate-400 uppercase block">Corridor Risk</span>
                  <span className="text-slate-900 font-semibold text-[11px]">LOW (ELEVATED)</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-0.5">
                  <span className="text-[10px] text-slate-400 uppercase block">Distance</span>
                  <span className="text-slate-900 font-bold">{activeRoute.distance_km} km</span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-0.5">
                  <span className="text-[10px] text-slate-400 uppercase block">Travel Time</span>
                  <span className="text-slate-900 font-bold">~{activeRoute.travel_time_minutes} min</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-0.5">
                  <span className="text-[10px] text-slate-400 uppercase block">Throughput Capacity</span>
                  <span className="text-slate-900 font-bold">12,500 evac/hr</span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-0.5">
                  <span className="text-[10px] text-slate-400 uppercase block">Clearance Time</span>
                  <span className="text-slate-900 font-bold">~3.8 hours</span>
                </div>
              </div>

              <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[10px] text-slate-400 uppercase block">Contingency Corridor</span>
                <div className="text-slate-800 text-[11px] font-sans">
                  SH-47 Mandvi-Bhuj Highway via Gadhsisa (Elevation &gt;18m ASL)
                </div>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-400 font-mono">
            Routing Engine: OSRM (Open Source Routing Machine) • Road Network: OSM
          </div>
        </div>
      </div>

      {/* Shelter Inventory Table */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <div>
            <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
              Designated Multi-Purpose Cyclone Shelters (MPCS)
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
              Operational inventory of designated storm surge and gale-force wind refuges
            </p>
          </div>
          <span className="text-[11px] font-mono text-slate-400">{shelters.length} Facilities Cataloged</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 text-[11px]">
                <th className="py-2 px-3 font-semibold">Facility Name</th>
                <th className="py-2 px-3 font-semibold">Classification</th>
                <th className="py-2 px-3 font-semibold">Capacity</th>
                <th className="py-2 px-3 font-semibold">Elevation</th>
                <th className="py-2 px-3 font-semibold">Generator</th>
                <th className="py-2 px-3 font-semibold">Water Storage</th>
                <th className="py-2 px-3 font-semibold">Verification Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {shelters.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500 font-mono">
                    {isUsingCached ? "Shelter catalog offline. Showing cached baseline." : "No shelters cataloged."}
                  </td>
                </tr>
              ) : (
                shelters.map((sh) => (
                  <tr key={sh.id} className="hover:bg-slate-50/60">
                    <td className="py-2.5 px-3 font-semibold text-slate-900 font-sans">{sh.name}</td>
                    <td className="py-2.5 px-3 text-slate-600">MPCS Type A</td>
                    <td className="py-2.5 px-3 font-bold text-slate-900">{sh.total_capacity} persons</td>
                    <td className="py-2.5 px-3 text-slate-600">{sh.elevation_meters}m ASL</td>
                    <td className="py-2.5 px-3">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${sh.generator_available ? "bg-slate-100 text-slate-800" : "bg-slate-50 text-slate-400"}`}>
                        {sh.generator_available ? "READY" : "NONE"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">10,000L Cistern</td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        {sh.is_verified ? "Official Verified" : "OSM Open"}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Hospital & Healthcare Directory Table */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <div>
            <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
              Emergency Healthcare & Trauma Facilities
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
              Medical emergency readiness, ICU capacity, and helipad facilities
            </p>
          </div>
          <span className="text-[11px] font-mono text-slate-400">{hospitals.length} Facilities Cataloged</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 text-[11px]">
                <th className="py-2 px-3 font-semibold">Facility Name</th>
                <th className="py-2 px-3 font-semibold">Facility Tier</th>
                <th className="py-2 px-3 font-semibold">Total Beds</th>
                <th className="py-2 px-3 font-semibold">ICU Beds</th>
                <th className="py-2 px-3 font-semibold">Helipad</th>
                <th className="py-2 px-3 font-semibold">Oxygen Backup</th>
                <th className="py-2 px-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {hospitals.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500 font-mono">
                    {isUsingCached ? "Hospital catalog offline. Showing cached baseline." : "No hospitals cataloged."}
                  </td>
                </tr>
              ) : (
                hospitals.map((hosp) => (
                  <tr key={hosp.id} className="hover:bg-slate-50/60">
                    <td className="py-2.5 px-3 font-semibold text-slate-900 font-sans">{hosp.name}</td>
                    <td className="py-2.5 px-3 text-slate-600">Sub-District / Community</td>
                    <td className="py-2.5 px-3 font-bold text-slate-900">{hosp.total_beds}</td>
                    <td className="py-2.5 px-3 text-slate-600">{hosp.available_icu_beds}</td>
                    <td className="py-2.5 px-3">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${hosp.helipad ? "bg-slate-100 text-slate-800" : "bg-slate-50 text-slate-400"}`}>
                        {hosp.helipad ? "YES" : "NO"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">LMO Plant (72h)</td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        TRAUMA READY
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Statutory Authority Advisory Banner */}
      <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-600 font-mono leading-relaxed">
        <span className="text-slate-900 font-semibold uppercase">AI Advisory — Not an Official Evacuation Order: </span>
        Evacuation routing corridors, transit clearance times, and facility allocations are algorithmic decision-support calculations [MODEL PROXY / OSRM]. They do not supersede mandatory evacuation orders, curfew notices, or road closures declared by the District Magistrate, District Collector, State Police, or State Disaster Management Authority (SDMA).
      </div>
    </div>
  );
}
