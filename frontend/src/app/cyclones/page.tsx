"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, ShieldAlert, Search } from "lucide-react";
import { fetchFromAPI } from "@/lib/api";

export default function CyclonesPage() {
  const [cyclones, setCyclones] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBasin, setSelectedBasin] = useState("All");

  useEffect(() => {
    let mounted = true;
    async function loadCyclones() {
      setLoading(true);
      const data = await fetchFromAPI("/cyclones");
      if (mounted) {
        if (Array.isArray(data) && data.length > 0) {
          setCyclones(data);
          setIsOffline(false);
        } else {
          setIsOffline(true);
        }
        setLoading(false);
      }
    }
    loadCyclones();
    return () => { mounted = false; };
  }, []);

  const filtered = cyclones.filter(c => {
    const matchesSearch = (c.name || "").toLowerCase().includes(searchQuery.toLowerCase()) || 
                          (c.current_category || "").toLowerCase().includes(searchQuery.toLowerCase());
    const matchesBasin = selectedBasin === "All" || 
                         (c.basin && c.basin.toLowerCase().includes(selectedBasin.toLowerCase()));
    return matchesSearch && matchesBasin;
  });

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6">
      {/* Offline Alert Banner */}
      {isOffline && (
        <div className="p-3 bg-amber-50 border border-amber-300 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-amber-900 font-mono">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Offline Mode:</strong> Backend API unreachable. Unable to sync cyclone catalog.
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
              NORTH INDIAN OCEAN CYCLONE CATALOG
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Active and historical cyclonic systems across Arabian Sea & Bay of Bengal • NOAA IBTrACS & IMD Archives
            </p>
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            REGISTRY: NOAA IBTrACS v04r00 / RSMC NEW DELHI
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white border border-slate-200 rounded p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search cyclone by name (e.g. BIPARJOY, AMPHAN, TAUKTAE)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:outline-none focus:border-slate-400 text-slate-900 font-mono"
          />
        </div>

        <div className="flex items-center space-x-1.5 text-xs font-mono">
          <span className="text-slate-400 mr-1 text-[11px] uppercase">Basin:</span>
          {["All", "Arabian Sea", "Bay of Bengal"].map((basin) => (
            <button
              key={basin}
              onClick={() => setSelectedBasin(basin)}
              className={`px-2.5 py-1 rounded text-xs transition ${
                selectedBasin === basin 
                  ? "bg-slate-900 text-white font-semibold" 
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {basin}
            </button>
          ))}
        </div>
      </div>

      {/* Cyclones Registry Table */}
      {loading ? (
        <div className="bg-white border border-slate-200 rounded p-12 text-center text-xs font-mono text-slate-500">
          <span>Loading North Indian Ocean Cyclone Catalog...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded p-12 text-center text-xs font-mono text-slate-500 space-y-2">
          {isOffline ? (
            <>
              <ShieldAlert className="w-5 h-5 text-amber-600 mx-auto" />
              <div className="font-semibold text-slate-800">Catalog Offline</div>
              <p className="text-slate-500">
                Could not connect to CycloneX backend service.
              </p>
            </>
          ) : (
            <span>No cyclonic systems match the query "{searchQuery}" in {selectedBasin}.</span>
          )}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div>
              <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
                North Indian Ocean Historical & Monitored Storms
              </h2>
              <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
                NOAA IBTrACS v04r00 & RSMC New Delhi synoptic archive
              </p>
            </div>
            <span className="text-[11px] font-mono text-slate-400">{filtered.length} Storms Listed</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 text-[11px]">
                  <th className="py-2.5 px-3 font-semibold">Cyclone Name</th>
                  <th className="py-2.5 px-3 font-semibold">Basin</th>
                  <th className="py-2.5 px-3 font-semibold">IMD Classification</th>
                  <th className="py-2.5 px-3 font-semibold">Center Coords</th>
                  <th className="py-2.5 px-3 font-semibold">Max Wind</th>
                  <th className="py-2.5 px-3 font-semibold">Min Pressure</th>
                  <th className="py-2.5 px-3 font-semibold">Risk Tier</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Dossier</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/60 transition">
                    <td className="py-2.5 px-3 font-semibold text-slate-900 font-sans">
                      <Link href={`/cyclones/${c.id}`} className="hover:underline">
                        Cyclone {c.name}
                      </Link>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">{c.basin}</td>
                    <td className="py-2.5 px-3 text-slate-700 font-sans">{c.current_category}</td>
                    <td className="py-2.5 px-3 text-slate-600">{c.current_lat}°N, {c.current_lon}°E</td>
                    <td className="py-2.5 px-3 font-bold text-slate-900">{c.current_wind_speed_kts} kts</td>
                    <td className="py-2.5 px-3 text-slate-600">{c.current_pressure_hpa} hPa</td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-800">
                        {c.risk_level || "HIGH"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        {c.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <Link
                        href={`/cyclones/${c.id}`}
                        className="inline-flex items-center space-x-1 text-slate-700 hover:text-slate-900 font-medium hover:underline text-[11px]"
                      >
                        <span>View</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
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
