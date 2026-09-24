"use client";

import { useEffect, useState, useRef } from "react";
import { usePathname } from "next/navigation";
import { Menu, Maximize2, Minimize2, Activity, Server, Database, CloudSun, ShieldAlert, Truck, Bell, RefreshCw, X } from "lucide-react";
import { fetchFromAPI, getApiBaseUrl } from "@/lib/api";

interface TopHeaderProps {
  onToggleSidebar?: () => void;
}

const ROUTE_TITLES: Record<string, string> = {
  "/dashboard": "Command Center / Live Monitoring",
  "/forecast": "Trajectory & Intensity Forecast",
  "/risk": "Risk & Impact Assessment (UNDRR)",
  "/evacuation": "Evacuation Logistics & Shelters",
  "/alerts": "Operational Early Warning Inbox",
  "/cyclones": "North Indian Ocean Cyclone Catalog",
  "/historical": "Historical Cyclone Analogs",
  "/model-performance": "Model Performance & Scientific Validation",
  "/demo": "Operational Demonstration",
  "/judge-qa": "Jury Q&A & Technical Defense",
};

export default function TopHeader({ onToggleSidebar }: TopHeaderProps) {
  const pathname = usePathname();
  const [systemStatus, setSystemStatus] = useState<"CHECKING" | "OPERATIONAL" | "DEGRADED" | "OFFLINE">("CHECKING");
  const [servicesState, setServicesState] = useState({
    api: "CHECKING",
    weather: "CHECKING",
    risk: "CHECKING",
    logistics: "CHECKING",
    alerts: "CHECKING",
    database: "CHECKING",
    map: "AVAILABLE"
  });
  const [lastCheckTime, setLastCheckTime] = useState<string>("");
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isPresentationMode, setIsPresentationMode] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  const checkHealth = async () => {
    setIsRefreshing(true);
    const nowIso = new Date().toISOString();
    setLastCheckTime(nowIso);

    try {
      const h = await fetchFromAPI("/system/health");

      if (!h || (h.status !== "ok" && h.status !== "healthy")) {
        // Core API unreachable
        setSystemStatus("OFFLINE");
        setServicesState({
          api: "OFFLINE",
          weather: "OFFLINE",
          risk: "OFFLINE",
          logistics: "OFFLINE",
          alerts: "OFFLINE",
          database: "OFFLINE",
          map: "AVAILABLE"
        });
        return;
      }

      // Core API responded with 200
      const dbConnected = h.database === "connected";
      let isDegraded = !dbConnected;

      // Check weather status
      let weatherStatus = "LIVE";
      try {
        const w = await fetchFromAPI("/weather/live?target=most_disturbed");
        if (!w) {
          weatherStatus = "OFFLINE";
          isDegraded = true;
        } else if (w.status === "STALE" || w.data_status === "STALE") {
          weatherStatus = "STALE";
          isDegraded = true;
        } else if (w.status === "OFFLINE" || w.data_status === "OFFLINE") {
          weatherStatus = "OFFLINE";
          isDegraded = true;
        }
      } catch {
        weatherStatus = "OFFLINE";
        isDegraded = true;
      }

      setServicesState({
        api: "LIVE",
        weather: weatherStatus,
        risk: "LIVE",
        logistics: "LIVE",
        alerts: "READY",
        database: dbConnected ? "CONNECTED" : "OFFLINE",
        map: "AVAILABLE"
      });

      setSystemStatus(isDegraded ? "DEGRADED" : "OPERATIONAL");
    } catch {
      setSystemStatus("OFFLINE");
      setServicesState({
        api: "OFFLINE",
        weather: "OFFLINE",
        risk: "OFFLINE",
        logistics: "OFFLINE",
        alerts: "OFFLINE",
        database: "OFFLINE",
        map: "AVAILABLE"
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [pathname]);

  const togglePresentation = () => {
    if (typeof document !== "undefined") {
      const active = document.body.classList.toggle("presentation-active");
      setIsPresentationMode(active);
    }
  };

  const currentTitle = ROUTE_TITLES[pathname] || "Operational Control Room";
  const activeBaseUrl = getApiBaseUrl();

  return (
    <header className="h-[54px] px-6 bg-white border-b border-slate-200 flex items-center justify-between sticky top-0 z-20 select-none">
      {/* LEFT: Dynamic Operational View Title */}
      <div className="flex items-center space-x-3">
        {onToggleSidebar && (
          <button 
            onClick={onToggleSidebar}
            className="md:hidden p-1 rounded hover:bg-slate-100 text-slate-500"
            title="Toggle Menu"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}
        <div className="text-xs font-semibold text-slate-800 tracking-tight">
          {currentTitle}
        </div>
      </div>

      {/* RIGHT: PRESENTATION TOGGLE, DATA, UPDATED, SYSTEM */}
      <div className="flex items-center space-x-5 text-xs">
        {/* Presentation / Projector Mode Toggle */}
        <button
          onClick={togglePresentation}
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-mono transition border ${
            isPresentationMode
              ? "bg-slate-900 text-white border-slate-900 font-semibold"
              : "bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200"
          }`}
          title={isPresentationMode ? "Exit Projection Mode" : "Maximize view for big screen projector"}
        >
          {isPresentationMode ? (
            <>
              <Minimize2 className="w-3.5 h-3.5" />
              <span>EXIT PROJECTION</span>
            </>
          ) : (
            <>
              <Maximize2 className="w-3.5 h-3.5 text-slate-500" />
              <span>PROJECTION MODE</span>
            </>
          )}
        </button>

        <div className="hidden sm:flex flex-col text-right">
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider leading-none">DATA</span>
          <span className="text-slate-800 font-medium leading-tight mt-0.5">NOAA / IMD</span>
        </div>

        <div className="hidden sm:flex flex-col text-right">
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider leading-none">UPDATED</span>
          <span className="text-slate-800 font-medium font-mono leading-tight mt-0.5">
            {lastCheckTime ? new Date(lastCheckTime).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit" }) + " IST" : "Syncing"}
          </span>
        </div>

        {/* SYSTEM STATUS PILL & CLICKABLE STATUS MODAL TRIGGER */}
        <button
          onClick={() => setShowStatusModal(!showStatusModal)}
          className="flex flex-col text-right hover:opacity-80 transition cursor-pointer"
          title="Click to view full Production Service Status Panel"
        >
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider leading-none">SYSTEM</span>
          <div className="flex items-center justify-end space-x-1.5 font-medium text-slate-800 leading-tight mt-0.5">
            <span
              className={`w-2 h-2 rounded-full ${
                systemStatus === "OPERATIONAL"
                  ? "bg-emerald-500"
                  : systemStatus === "DEGRADED"
                  ? "bg-amber-500 animate-pulse"
                  : systemStatus === "OFFLINE"
                  ? "bg-rose-600 animate-pulse"
                  : "bg-slate-400 animate-pulse"
              }`}
            />
            <span className={`font-semibold ${
              systemStatus === "OPERATIONAL"
                ? "text-emerald-700"
                : systemStatus === "DEGRADED"
                ? "text-amber-700"
                : systemStatus === "OFFLINE"
                ? "text-rose-700"
                : "text-slate-500"
            }`}>
              {systemStatus === "OPERATIONAL"
                ? "Operational"
                : systemStatus === "DEGRADED"
                ? "Degraded"
                : systemStatus === "OFFLINE"
                ? "Offline"
                : "Checking..."}
            </span>
          </div>
        </button>
      </div>

      {/* PRODUCTION SERVICE STATUS PANEL MODAL */}
      {showStatusModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div
            ref={modalRef}
            className="bg-white border border-slate-200 rounded-lg shadow-2xl max-w-md w-full p-5 space-y-4 font-mono text-xs animate-in fade-in zoom-in-95 duration-150"
          >
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center space-x-2">
                <Activity className="w-4 h-4 text-blue-600" />
                <span className="font-bold text-slate-900 text-sm">Production Services Status</span>
              </div>
              <button
                onClick={() => setShowStatusModal(false)}
                className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Overall Status Banner */}
            <div className={`p-3 rounded border flex items-center justify-between ${
              systemStatus === "OPERATIONAL"
                ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                : systemStatus === "DEGRADED"
                ? "bg-amber-50 border-amber-200 text-amber-900"
                : "bg-rose-50 border-rose-200 text-rose-900"
            }`}>
              <div className="flex items-center space-x-2">
                <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                  systemStatus === "OPERATIONAL"
                    ? "bg-emerald-500"
                    : systemStatus === "DEGRADED"
                    ? "bg-amber-500 animate-pulse"
                    : "bg-rose-500 animate-pulse"
                }`} />
                <span className="font-bold">SYSTEM STATUS: {systemStatus}</span>
              </div>
              <button
                onClick={checkHealth}
                disabled={isRefreshing}
                className="flex items-center space-x-1 px-2 py-0.5 rounded bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 transition text-[11px]"
              >
                <RefreshCw className={`w-3 h-3 ${isRefreshing ? "animate-spin text-blue-600" : ""}`} />
                <span>Refresh</span>
              </button>
            </div>

            {/* Service Matrix Table */}
            <div className="space-y-1.5 border border-slate-200 rounded p-2.5 bg-slate-50/50">
              <div className="flex items-center justify-between py-1 border-b border-slate-200 text-slate-500 text-[11px]">
                <span>SUBSYSTEM</span>
                <span>STATUS</span>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="flex items-center space-x-2 text-slate-700">
                  <Server className="w-3.5 h-3.5 text-slate-400" />
                  <span>FastAPI Core API</span>
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  servicesState.api === "LIVE" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                }`}>
                  {servicesState.api}
                </span>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="flex items-center space-x-2 text-slate-700">
                  <CloudSun className="w-3.5 h-3.5 text-slate-400" />
                  <span>Open-Meteo Weather</span>
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  servicesState.weather === "LIVE"
                    ? "bg-emerald-100 text-emerald-800"
                    : servicesState.weather === "STALE"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-rose-100 text-rose-800"
                }`}>
                  {servicesState.weather}
                </span>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="flex items-center space-x-2 text-slate-700">
                  <ShieldAlert className="w-3.5 h-3.5 text-slate-400" />
                  <span>Risk Intelligence Engine</span>
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  servicesState.risk === "LIVE" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                }`}>
                  {servicesState.risk}
                </span>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="flex items-center space-x-2 text-slate-700">
                  <Truck className="w-3.5 h-3.5 text-slate-400" />
                  <span>Logistics & Evacuation</span>
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  servicesState.logistics === "LIVE" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                }`}>
                  {servicesState.logistics}
                </span>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="flex items-center space-x-2 text-slate-700">
                  <Bell className="w-3.5 h-3.5 text-slate-400" />
                  <span>Early Warning Alerts</span>
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  servicesState.alerts === "READY" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                }`}>
                  {servicesState.alerts}
                </span>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="flex items-center space-x-2 text-slate-700">
                  <Database className="w-3.5 h-3.5 text-slate-400" />
                  <span>Database State</span>
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  servicesState.database === "CONNECTED" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                }`}>
                  {servicesState.database}
                </span>
              </div>

              <div className="flex items-center justify-between py-1">
                <span className="flex items-center space-x-2 text-slate-700">
                  <Activity className="w-3.5 h-3.5 text-slate-400" />
                  <span>GIS & Map Layers</span>
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                  AVAILABLE
                </span>
              </div>
            </div>

            {/* Target URL & Diagnostic Info */}
            <div className="p-2.5 rounded bg-slate-100 text-[11px] text-slate-600 space-y-1">
              <div>
                <strong>Active Target:</strong>{" "}
                <span className="text-slate-800 break-all">{activeBaseUrl}</span>
              </div>
              <div>
                <strong>Last Checked:</strong>{" "}
                <span>
                  {lastCheckTime
                    ? `${new Date(lastCheckTime).toISOString().replace("T", " ").substring(0, 19)} UTC`
                    : "--"}
                </span>
              </div>
              {systemStatus === "OFFLINE" && (
                <div className="text-rose-700 mt-1 font-sans text-[11px]">
                  <strong>Action Required:</strong> The FastAPI backend is not deployed to the cloud. Deploy the backend on Render/Railway and set <code className="bg-rose-100 px-1 rounded">NEXT_PUBLIC_API_BASE_URL</code> in Vercel.
                </div>
              )}
            </div>

            <button
              onClick={() => setShowStatusModal(false)}
              className="w-full py-1.5 rounded bg-slate-800 hover:bg-slate-900 text-white font-medium transition text-center"
            >
              Close Status Panel
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
