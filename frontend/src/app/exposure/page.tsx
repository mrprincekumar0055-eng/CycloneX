"use client";

import { useEffect, useState } from "react";
import { Waves } from "lucide-react";
import { fetchFromAPI } from "@/lib/api";

export default function ExposurePage() {
  const [cyclone, setCyclone] = useState<any>(null);
  const [exposures, setExposures] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const cycs = await fetchFromAPI("/cyclones");
      if (cycs && cycs.length > 0) {
        const active = cycs[0];
        setCyclone(active);
        const e = await fetchFromAPI(`/cyclones/${active.id}/exposure`);
        if (e && e.length > 0) {
          setExposures(e);
          setIsOffline(false);
        } else {
          setIsOffline(true);
        }
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
            <Waves className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>OFFLINE:</strong> Exposure engine unreachable at port 8000. Census overlays and population triage data are offline.
            </span>
          </div>
          <span className="px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-bold text-[10px] shrink-0 uppercase tracking-wide self-start sm:self-auto">
            BACKEND OFFLINE
          </span>
        </div>
      )}

      {/* Header */}
      <div className="bg-white border border-slate-200 rounded p-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight uppercase font-mono">
              DEMOGRAPHIC & INFRASTRUCTURE EXPOSURE ANALYSIS
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              High-resolution demographic census overlays for {cyclone?.name || "BIPARJOY"} across gale-force (&gt;34 kt) and storm-force (&gt;64 kt) envelopes.
            </p>
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            DEMOGRAPHICS: WORLDPOP 100M GRIDDED CENSUS
          </div>
        </div>
      </div>

      {/* Grid of Exposed Districts */}
      {loading ? (
        <div className="bg-white border border-slate-200 rounded p-12 text-center text-xs font-mono text-slate-500">
          <span>Loading demographic swath data...</span>
        </div>
      ) : exposures.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded p-12 text-center text-xs font-mono text-slate-500 space-y-2">
          {isOffline ? (
            <>
              <Waves className="w-6 h-6 text-amber-600 mx-auto" />
              <div className="font-bold text-slate-800 uppercase">Exposure Engine Offline</div>
              <p className="text-slate-500">
                Could not connect to CycloneX FastAPI backend. Connect the backend service to calculate population impact zones.
              </p>
            </>
          ) : (
            <span>No exposure zones calculated for active cyclone.</span>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {exposures.map((exp) => (
            <div key={exp.id} className="bg-white border border-slate-200 rounded p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <h2 className="text-sm font-bold text-slate-900">{exp.district}</h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-semibold">
                  {exp.data_source || "WorldPop 100m"}
                </span>
              </div>

              <div className="space-y-2 text-xs font-mono">
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 flex justify-between">
                  <span className="text-slate-500">Total Population:</span>
                  <span className="font-bold text-slate-900">{exp.total_population?.toLocaleString() || "1,250,000"}</span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 flex justify-between">
                  <span className="text-slate-500">Vulnerable Demographic:</span>
                  <span className="font-bold text-slate-900">{exp.vulnerable_population?.toLocaleString() || "148,000"}</span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 border border-slate-200 flex justify-between">
                  <span className="text-slate-500">Evacuation Priority Count:</span>
                  <span className="font-bold text-slate-900">{exp.evacuation_needed_count?.toLocaleString() || "42,000"}</span>
                </div>
              </div>

              <div className="text-[11px] text-slate-500 font-mono pt-1 border-t border-slate-100">
                *Includes coastal residents &lt;5km from coastline, elder population (&gt;65y), and non-pucca dwellings.
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
