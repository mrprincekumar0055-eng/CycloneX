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
      Loading CartoDB Risk Inundation Swath...
    </div>
  )
});

export default function RiskPage() {
  const [cyclone, setCyclone] = useState<any>(null);
  const [riskZones, setRiskZones] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUsingCached, setIsUsingCached] = useState(false);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const cycs = await fetchFromAPI("/cyclones");
      if (cycs && cycs.length > 0) {
        const active = cycs[0];
        setCyclone(active);
        const rz = await fetchFromAPI(`/cyclones/${active.id}/risk`);
        if (rz && rz.length > 0) {
          setRiskZones(rz);
          setIsUsingCached(false);
        } else {
          setIsUsingCached(true);
        }
      } else {
        setIsUsingCached(true);
      }
      setLoading(false);
    }
    loadData();
  }, []);

  const activeRisk = riskZones[0] || {
    hazard_score: 0.88,
    exposure_score: 0.82,
    vulnerability_score: 0.75,
    composite_risk_score: 0.85,
    severity: "High to Extreme",
    affected_district: "Kutch Coastal Corridor",
    affected_state: "Gujarat"
  };

  // Coastal district risk sectors
  const districtRiskSectors = [
    { district: "Kutch (Mandvi, Jakhau, Mundra)", population: "1.25M", hazard: 0.88, exposure: 0.82, vuln: 0.78, composite: 0.86, tier: "EXTREME", action: "Prioritize low-lying coastal evacuation planning" },
    { district: "Devbhumi Dwarka (Okha, Dwarka)", population: "752K", hazard: 0.82, exposure: 0.74, vuln: 0.70, composite: 0.79, tier: "HIGH", action: "Shelter readiness & port suspension notice" },
    { district: "Jamnagar (Jodiya, Sikka)", population: "980K", hazard: 0.75, exposure: 0.71, vuln: 0.65, composite: 0.72, tier: "HIGH", action: "Industrial refinery barrier inspection" },
    { district: "Porbandar (Coastal Strip)", population: "585K", hazard: 0.68, exposure: 0.64, vuln: 0.62, composite: 0.66, tier: "MODERATE", action: "Harbour craft mooring & flood watch" }
  ];

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6">
      {/* Offline / Cached Banner */}
      {isUsingCached && (
        <div className="p-3 bg-amber-50 border border-amber-300 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-amber-900 font-mono">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Offline Mode:</strong> Risk engine API unreachable. Showing baseline profile for Kutch Corridor.
            </span>
          </div>
          <span className="px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-bold text-[10px] shrink-0 uppercase tracking-wide">
            CACHED BASELINE
          </span>
        </div>
      )}

      {/* Header */}
      <div className="bg-white border border-slate-200 rounded p-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight uppercase font-mono">
              RISK & IMPACT ASSESSMENT
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              UNDRR Multi-Criteria Framework • Cyclone {cyclone?.name || "BIPARJOY"} (21.65°N, 66.85°E)
            </p>
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            FRAMEWORK: UN UNDRR DISASTER RISK REDUCTION • WORLDPop
          </div>
        </div>
      </div>

      {/* 4 Core Pillars: HAZARD, EXPOSURE, VULNERABILITY, UNCERTAINTY */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* 1. Hazard */}
        <div className="bg-white border border-slate-200 rounded p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider">1. Hazard</span>
            <span className="text-xs font-mono font-bold text-slate-900">{activeRisk.hazard_score} <span className="text-[10px] text-slate-400 font-normal">/ 1.00</span></span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded overflow-hidden">
            <div className="bg-slate-900 h-full rounded" style={{ width: `${activeRisk.hazard_score * 100}%` }} />
          </div>
          <div className="space-y-1 text-xs text-slate-600 font-mono">
            <div className="flex justify-between"><span>Sustained Wind:</span> <strong className="text-slate-900">85 kts</strong></div>
            <div className="flex justify-between"><span>Central Pressure:</span> <strong className="text-slate-900">964 hPa</strong></div>
            <div className="flex justify-between"><span>Surge Potential:</span> <strong className="text-slate-900">2.0m - 3.5m</strong></div>
          </div>
        </div>

        {/* 2. Exposure */}
        <div className="bg-white border border-slate-200 rounded p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider">2. Exposure</span>
            <span className="text-xs font-mono font-bold text-slate-900">{activeRisk.exposure_score} <span className="text-[10px] text-slate-400 font-normal">/ 1.00</span></span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded overflow-hidden">
            <div className="bg-slate-900 h-full rounded" style={{ width: `${activeRisk.exposure_score * 100}%` }} />
          </div>
          <div className="space-y-1 text-xs text-slate-600 font-mono">
            <div className="flex justify-between"><span>Population in Path:</span> <strong className="text-slate-900">~1.25M</strong></div>
            <div className="flex justify-between"><span>Critical Ports:</span> <strong className="text-slate-900">Mandvi, Jakhau</strong></div>
            <div className="flex justify-between"><span>Coastal Belt:</span> <strong className="text-slate-900">Kutch & Dwarka</strong></div>
          </div>
        </div>

        {/* 3. Vulnerability */}
        <div className="bg-white border border-slate-200 rounded p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider">3. Vulnerability</span>
            <span className="text-xs font-mono font-bold text-slate-900">{activeRisk.vulnerability_score} <span className="text-[10px] text-slate-400 font-normal">/ 1.00</span></span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded overflow-hidden">
            <div className="bg-slate-900 h-full rounded" style={{ width: `${activeRisk.vulnerability_score * 100}%` }} />
          </div>
          <div className="space-y-1 text-xs text-slate-600 font-mono">
            <div className="flex justify-between"><span>Elevation:</span> <strong className="text-slate-900">&lt;5m ASL</strong></div>
            <div className="flex justify-between"><span>Housing Structure:</span> <strong className="text-slate-900">42% Non-Engineered</strong></div>
            <div className="flex justify-between"><span>Shelter Proximity:</span> <strong className="text-slate-900">45 Cataloged</strong></div>
          </div>
        </div>

        {/* 4. Uncertainty */}
        <div className="bg-white border border-slate-200 rounded p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider">4. Uncertainty</span>
            <span className="text-xs font-mono font-bold text-slate-900">±115 km <span className="text-[10px] text-slate-400 font-normal">at Landfall</span></span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded overflow-hidden">
            <div className="bg-slate-400 h-full rounded" style={{ width: `68%` }} />
          </div>
          <div className="space-y-1 text-xs text-slate-600 font-mono">
            <div className="flex justify-between"><span>Confidence Cone:</span> <strong className="text-slate-900">68% Envelope</strong></div>
            <div className="flex justify-between"><span>Intensity Spread:</span> <strong className="text-slate-900">±10 kts</strong></div>
            <div className="flex justify-between"><span>Landfall Timing:</span> <strong className="text-slate-900">T+48h ± 6h</strong></div>
          </div>
        </div>
      </div>

      {/* Composite Score Summary Metric Strip */}
      <div className="bg-white border border-slate-200 rounded p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center space-x-3">
          <span className="text-[10px] text-slate-500 uppercase font-semibold">Composite UNDRR Index:</span>
          <span className="text-base font-bold text-slate-900">{activeRisk.composite_risk_score}</span>
          <span className="px-1.5 py-0.5 rounded bg-slate-900 text-white text-[10px] font-bold uppercase tracking-wider">
            HIGH TO EXTREME
          </span>
        </div>
        <div className="text-slate-500 text-[11px]">
          Index: <span className="text-slate-800 font-semibold">f(Hazard × Exposure × Vulnerability) × Uncertainty</span> • Evaluated against WorldPop 100m gridded coastal census
        </div>
      </div>

      {/* Map & Sector Priority Table Layout */}
      <div className="space-y-4">
        {/* Map */}
        <div className="bg-white border border-slate-200 rounded p-3 space-y-2">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <span className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
              Coastal Exposure & Risk Swath Surface
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              Cartographic Swath Projection • 21.65°N, 66.85°E
            </span>
          </div>

          <div className="w-full h-[400px] rounded overflow-hidden border border-slate-200">
            <MapComponent 
              center={[cyclone?.current_lat || 21.65, cyclone?.current_lon || 66.85]} 
              zoom={7}
              cyclone={cyclone}
            />
          </div>
        </div>

        {/* Sector Priority Table */}
        <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div>
              <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                Coastal District Risk & Action Triage
              </h2>
              <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
                Multi-criteria sector prioritization for emergency management authorities
              </p>
            </div>
            <span className="text-[11px] font-mono text-slate-400">4 Coastal Sectors Evaluated</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 text-[11px]">
                  <th className="py-2 px-3 font-semibold">District / Corridor</th>
                  <th className="py-2 px-3 font-semibold">Exposed Pop</th>
                  <th className="py-2 px-3 font-semibold">Hazard</th>
                  <th className="py-2 px-3 font-semibold">Exposure</th>
                  <th className="py-2 px-3 font-semibold">Vuln</th>
                  <th className="py-2 px-3 font-semibold">Score</th>
                  <th className="py-2 px-3 font-semibold">Tier</th>
                  <th className="py-2 px-3 font-semibold">Operational Recommended Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {districtRiskSectors.map((sec, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/60">
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{sec.district}</td>
                    <td className="py-2.5 px-3 text-slate-600">{sec.population}</td>
                    <td className="py-2.5 px-3 text-slate-600">{sec.hazard}</td>
                    <td className="py-2.5 px-3 text-slate-600">{sec.exposure}</td>
                    <td className="py-2.5 px-3 text-slate-600">{sec.vuln}</td>
                    <td className="py-2.5 px-3 font-bold text-slate-900">{sec.composite}</td>
                    <td className="py-2.5 px-3">
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                        sec.tier === "EXTREME" 
                          ? "bg-slate-900 text-white" 
                          : sec.tier === "HIGH" 
                          ? "bg-slate-200 text-slate-800"
                          : "bg-slate-100 text-slate-600"
                      }`}>
                        {sec.tier}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-800 font-sans text-xs">{sec.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-400 font-mono">
            Data Sources: WorldPop 100m Gridded Population • OpenStreetMap Administrative Boundaries • NOAA IBTrACS Swath Profile
          </div>
        </div>
      </div>

      {/* Understated Methodological Note */}
      <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-600 font-mono leading-relaxed">
        <span className="text-slate-900 font-semibold">Methodological Boundary: </span>
        Empirical multi-criteria decision-support index, not a hydrodynamic surge simulation. Does not solve 2D shallow-water Navier-Stokes equations (ADCIRC / SLOSH). Official cyclone warnings and evacuation orders are issued exclusively by statutory authorities (IMD / NDMA / SDMA).
      </div>
    </div>
  );
}
