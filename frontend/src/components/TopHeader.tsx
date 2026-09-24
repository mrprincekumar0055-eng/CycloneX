"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Menu, Maximize2, Minimize2 } from "lucide-react";
import { fetchFromAPI } from "@/lib/api";

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
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(true);
  const [isPresentationMode, setIsPresentationMode] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function checkHealth() {
      try {
        const h = await fetchFromAPI("/system/health");
        if (mounted) {
          setIsBackendOnline(h !== null && (h.status === "healthy" || h.status === "ok"));
        }
      } catch {
        if (mounted) setIsBackendOnline(false);
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, [pathname]);

  const togglePresentation = () => {
    if (typeof document !== "undefined") {
      const active = document.body.classList.toggle("presentation-active");
      setIsPresentationMode(active);
    }
  };

  const currentTitle = ROUTE_TITLES[pathname] || "Operational Control Room";

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
          <span className="text-slate-800 font-medium font-mono leading-tight mt-0.5">12:00 UTC</span>
        </div>

        <div className="flex flex-col text-right">
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider leading-none">SYSTEM</span>
          <div className="flex items-center justify-end space-x-1.5 font-medium text-slate-800 leading-tight mt-0.5">
            <span className={`w-1.5 h-1.5 rounded-full ${isBackendOnline === false ? "bg-red-600 animate-pulse" : "bg-emerald-600"}`} />
            <span>{isBackendOnline === false ? "Offline" : "Operational"}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
