"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Radar, Compass, ShieldAlert, 
  Navigation, Bell, 
  Activity, History, BarChart3, 
  Play, HelpCircle
} from "lucide-react";

interface SidebarProps {
  mobileOpen?: boolean;
  setMobileOpen?: (open: boolean) => void;
}

export default function Sidebar({ mobileOpen = false, setMobileOpen }: SidebarProps) {
  const pathname = usePathname();

  const operationsNav = [
    { name: "Command Center", href: "/dashboard", icon: Radar },
    { name: "Forecast & Track", href: "/forecast", icon: Compass },
    { name: "Risk & Exposure", href: "/risk", icon: ShieldAlert },
    { name: "Evacuation", href: "/evacuation", icon: Navigation },
    { name: "Alerts", href: "/alerts", icon: Bell },
  ];

  const dataAnalyticsNav = [
    { name: "Cyclones", href: "/cyclones", icon: Activity },
    { name: "Historical", href: "/historical", icon: History },
    { name: "ML Performance", href: "/model-performance", icon: BarChart3 },
  ];

  const demoNav = [
    { name: "3-Minute Demo", href: "/demo", icon: Play },
    { name: "Jury Q&A", href: "/judge-qa", icon: HelpCircle },
  ];

  const renderNavGroup = (title: string, items: typeof operationsNav) => (
    <div className="space-y-0.5">
      <div className="px-3 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
        {title}
      </div>
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = 
          item.href === "/dashboard" 
            ? pathname === "/dashboard" || pathname === "/"
            : pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));

        return (
          <Link
            key={item.name}
            href={item.href}
            onClick={() => setMobileOpen && setMobileOpen(false)}
            className={`flex items-center space-x-2.5 px-3 py-2 text-xs rounded-sm transition-colors ${
              isActive
                ? "bg-slate-100 text-slate-900 border-l-2 border-slate-900 font-medium"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-normal"
            }`}
          >
            <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-slate-900" : "text-slate-400"}`} />
            <span className="truncate">{item.name}</span>
          </Link>
        );
      })}
    </div>
  );

  return (
    <aside className="sidebar-nav-container fixed left-0 top-0 bottom-0 w-[240px] z-30 bg-white border-r border-slate-200 flex flex-col justify-between select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-200">
        <Link href="/dashboard" className="block">
          <div className="text-sm font-semibold tracking-wider text-slate-900">
            CYCLONEX
          </div>
          <div className="text-[11px] text-slate-500 font-normal mt-0.5">
            Early Warning & Decision Support
          </div>
        </Link>
      </div>

      {/* Navigation Groups */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
        {renderNavGroup("OPERATIONS", operationsNav)}
        <div className="border-t border-slate-100 mx-2" />
        {renderNavGroup("DATA & ANALYTICS", dataAnalyticsNav)}
        <div className="border-t border-slate-100 mx-2" />
        {renderNavGroup("DEMONSTRATION", demoNav)}
      </div>

      {/* System Status Footer */}
      <div className="p-3.5 border-t border-slate-200 bg-slate-50 text-[11px] text-slate-500 space-y-1">
        <div className="flex items-center space-x-1.5 text-slate-800 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
          <span>System Operational</span>
        </div>
        <div className="text-[10px] text-slate-400">NOAA / IMD / OSM</div>
        <div className="text-[10px] text-slate-400 font-mono">v1.0.0</div>
      </div>
    </aside>
  );
}
