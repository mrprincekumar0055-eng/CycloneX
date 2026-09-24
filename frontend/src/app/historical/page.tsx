"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Info, ShieldAlert } from "lucide-react";
import { fetchFromAPI } from "@/lib/api";

// Dynamic map import
const MapComponent = dynamic(() => import("@/components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[380px] bg-slate-50 border border-slate-200 rounded flex items-center justify-center text-slate-500 font-mono text-xs">
      Loading Historical Analog Map...
    </div>
  )
});

export default function HistoricalPage() {
  const [data, setData] = useState<any>(null);
  const [cyclone, setCyclone] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const [cycs, anData] = await Promise.all([
        fetchFromAPI("/cyclones"),
        fetchFromAPI("/historical/analogs?lat=21.65&lon=66.85&wind_speed_kts=85.0")
      ]);
      if (cycs && cycs.length > 0) setCyclone(cycs[0]);
      if (anData && anData.analogs && anData.analogs.length > 0) {
        setData(anData);
        setIsOffline(false);
      } else {
        setIsOffline(true);
      }
      setLoading(false);
    }
    load();
  }, []);

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6">
      {/* Offline Alert Banner */}
      {isOffline && (
        <div className="p-3 bg-amber-50 border border-amber-300 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-amber-900 font-mono">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Offline Mode:</strong> Historical pattern matching service unreachable. Showing cached analogs.
            </span>
          </div>
          <span className="px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-bold text-[10px] shrink-0 uppercase tracking-wide">
            OFFLINE
          </span>
        </div>
      )}

      {/* Header */}
      <div className="bg-white border border-slate-200 rounded p-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight uppercase font-mono">
              HISTORICAL CYCLONE ANALOGS
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Spatial & Kinematic Pattern Correlation • 40+ Years of North Indian Ocean Storms
            </p>
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            ANALOG ARCHIVE: NOAA NCEI IBTrACS v04r00
          </div>
        </div>
      </div>

      {/* Methodological Context Note */}
      <div className="p-4 rounded bg-slate-50 border border-slate-200 flex items-start space-x-3 text-xs text-slate-600 leading-relaxed">
        <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold text-slate-800">Operational Precedent Protocol: </strong> 
          Historical analogs provide comparative meteorological precedent for vulnerability triage and coastal impact scenarios. Analog similarity is an auxiliary reference and is not a forecast guarantee of future trajectory, landfall location, or storm intensity.
        </div>
      </div>

      {/* Synoptic Surface Map */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <span className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
            Active Storm vs Historical Analog Footprint
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            Anchor: 21.65°N, 66.85°E (85 kts)
          </span>
        </div>

        <div className="w-full h-[380px] rounded overflow-hidden border border-slate-200">
          <MapComponent 
            center={[21.65, 66.85]} 
            zoom={6}
            cyclone={cyclone}
          />
        </div>
      </div>

      {/* Analog Match Table */}
      {loading ? (
        <div className="bg-white border border-slate-200 rounded p-12 text-center text-xs font-mono text-slate-500">
          <span>Searching 40+ Years of NOAA IBTrACS Storm Tracks...</span>
        </div>
      ) : !data?.analogs || data.analogs.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded p-12 text-center text-xs font-mono text-slate-500 space-y-2">
          {isOffline ? (
            <>
              <ShieldAlert className="w-5 h-5 text-amber-600 mx-auto" />
              <div className="font-semibold text-slate-800">Historical Analogs Offline</div>
              <p className="text-slate-500">
                Could not connect to CycloneX backend service.
              </p>
            </>
          ) : (
            <span>No historical analogs match current storm coordinates and intensity profile.</span>
          )}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div>
              <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                Top Historical Cyclone Analogs (Spatial & Intensity Correlation)
              </h2>
              <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
                Nearest trajectory and central pressure profiles from NOAA NCEI IBTrACS archive
              </p>
            </div>
            <span className="text-[11px] font-mono text-slate-400">{data.analogs.length} Analogs Correlated</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 text-[11px]">
                  <th className="py-2.5 px-3 font-semibold">Cyclone Name</th>
                  <th className="py-2.5 px-3 font-semibold">Season / Basin</th>
                  <th className="py-2.5 px-3 font-semibold">Similarity Match</th>
                  <th className="py-2.5 px-3 font-semibold">Classification</th>
                  <th className="py-2.5 px-3 font-semibold">Peak Wind</th>
                  <th className="py-2.5 px-3 font-semibold">Min Pressure</th>
                  <th className="py-2.5 px-3 font-semibold">Historical Landfall Sector</th>
                  <th className="py-2.5 px-3 font-semibold text-right">IBTrACS SID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {data.analogs.map((an: any) => (
                  <tr key={an.sid} className="hover:bg-slate-50/60 transition">
                    <td className="py-2.5 px-3 font-semibold text-slate-900 font-sans">
                      Cyclone {an.name}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">{an.year} • {an.basin}</td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-900 text-white font-mono">
                        {an.similarity_score_pct}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 font-sans">{an.category}</td>
                    <td className="py-2.5 px-3 font-bold text-slate-900">{an.max_wind_kts} kts</td>
                    <td className="py-2.5 px-3 text-slate-600">{an.min_pressure_hpa} hPa</td>
                    <td className="py-2.5 px-3 text-slate-800 font-sans text-xs">{an.landfall_location}</td>
                    <td className="py-2.5 px-3 text-slate-500 text-right">{an.sid}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
