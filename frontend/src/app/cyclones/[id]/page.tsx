"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { fetchFromAPI } from "@/lib/api";

// Dynamic map import
const MapComponent = dynamic(() => import("@/components/MapComponent"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[380px] bg-slate-50 border border-slate-200 rounded flex items-center justify-center text-slate-500 font-mono text-xs">
      Loading Cyclone Synoptic Track Surface...
    </div>
  )
});

export default function CycloneDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const [cyclone, setCyclone] = useState<any>(null);
  const [track, setTrack] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    if (id) {
      setLoading(true);
      Promise.all([
        fetchFromAPI(`/cyclones/${id}`),
        fetchFromAPI(`/cyclones/${id}/track`),
        fetchFromAPI(`/cyclones/${id}/forecast`)
      ]).then(([c, t, f]) => {
        if (c) {
          setCyclone(c);
          setTrack(t || []);
          setForecast(f || null);
          setIsOffline(false);
        } else {
          setIsOffline(true);
        }
        setLoading(false);
      }).catch(() => {
        setIsOffline(true);
        setLoading(false);
      });
    }
  }, [id]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500 font-mono text-xs py-20">
        <span>Loading Cyclone Intelligence Profile...</span>
      </div>
    );
  }

  if (isOffline || !cyclone) {
    return (
      <div className="flex-1 p-8 max-w-2xl mx-auto text-center space-y-4 font-mono">
        <ShieldAlert className="w-6 h-6 text-amber-600 mx-auto" />
        <h2 className="text-sm font-semibold text-slate-900 uppercase">Cyclone Profile Unavailable</h2>
        <p className="text-xs text-slate-500">
          Could not retrieve storm record ({id}) from CycloneX backend service.
        </p>
        <Link href="/cyclones" className="inline-flex items-center space-x-1.5 text-xs text-slate-700 bg-slate-100 border border-slate-200 px-3 py-1.5 rounded hover:bg-slate-200 transition">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Cyclone Catalog</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6">
      <Link href="/cyclones" className="inline-flex items-center space-x-1.5 text-xs text-slate-500 hover:text-slate-800 transition font-mono">
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to All Cyclones</span>
      </Link>

      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">
              {cyclone.status} • {cyclone.basin}
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              {cyclone.status === "HISTORICAL" ? "HISTORICAL DATA" : "OPERATIONAL TARGET"}
            </span>
          </div>
          <h1 className="text-base font-bold font-mono text-slate-900 uppercase">Cyclone {cyclone.name}</h1>
          <p className="text-xs text-slate-600 font-medium mt-0.5">{cyclone.current_category}</p>
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="p-2 bg-slate-50 border border-slate-200 rounded">
            <span className="text-slate-400 block text-[10px] uppercase">Genesis</span>
            <span className="text-slate-900 font-semibold">{new Date(cyclone.genesis_time).toLocaleDateString()}</span>
          </div>
          <div className="p-2 bg-slate-50 border border-slate-200 rounded">
            <span className="text-slate-400 block text-[10px] uppercase">Risk Tier</span>
            <span className="text-slate-900 font-semibold">{cyclone.risk_level || "HIGH"}</span>
          </div>
          <Link
            href="/forecast"
            className="px-3 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-medium transition"
          >
            View Forecast →
          </Link>
        </div>
      </div>

      {/* Interactive Map */}
      <div className="bg-white border border-slate-200 rounded p-3 space-y-2">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <span className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
            Synoptic Track Trajectory
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            {track.length} Verified Synoptic Observations
          </span>
        </div>

        <div className="w-full h-[400px] rounded overflow-hidden border border-slate-200">
          <MapComponent 
            center={[cyclone?.current_lat || 21.65, cyclone?.current_lon || 66.85]} 
            zoom={6}
            cyclone={cyclone}
          />
        </div>
      </div>

      {/* Track Progression Table */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <div>
            <h2 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
              Observed Best Track Progression (NOAA IBTrACS)
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
              6-Hourly Synoptic Fixes synchronized with RSMC archives
            </p>
          </div>
          <span className="text-[11px] font-mono text-slate-400">{track.length} Observations</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 text-[11px]">
                <th className="py-2.5 px-3 font-semibold">UTC Timestamp</th>
                <th className="py-2.5 px-3 font-semibold">Latitude</th>
                <th className="py-2.5 px-3 font-semibold">Longitude</th>
                <th className="py-2.5 px-3 font-semibold">Sustained Wind</th>
                <th className="py-2.5 px-3 font-semibold">Pressure</th>
                <th className="py-2.5 px-3 font-semibold">IMD Category</th>
                <th className="py-2.5 px-3 font-semibold text-right">Agency Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {track.map((obs) => (
                <tr key={obs.id} className="hover:bg-slate-50/60 transition">
                  <td className="py-2.5 px-3">{new Date(obs.timestamp).toUTCString()}</td>
                  <td className="py-2.5 px-3">{obs.lat}°N</td>
                  <td className="py-2.5 px-3">{obs.lon}°E</td>
                  <td className="py-2.5 px-3 font-bold text-slate-900">{obs.wind_speed_kts} kts</td>
                  <td className="py-2.5 px-3">{obs.central_pressure_hpa} hPa</td>
                  <td className="py-2.5 px-3 text-slate-800 font-sans">{obs.imd_category}</td>
                  <td className="py-2.5 px-3 text-slate-400 text-right">{obs.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
