"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Radar, Activity, Compass, ShieldAlert, Users, 
  Navigation, History, Bell, Settings, Radio,
  Play, BarChart3, HelpCircle
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Command Center", href: "/dashboard", icon: Radar },
    { name: "Forecast & Track", href: "/forecast", icon: Compass },
    { name: "Risk & Exposure", href: "/risk", icon: ShieldAlert },
    { name: "Evacuation", href: "/evacuation", icon: Navigation },
    { name: "Cyclones", href: "/cyclones", icon: Activity },
    { name: "Historical", href: "/historical", icon: History },
    { name: "Alerts", href: "/alerts", icon: Bell },
  ];

  const grandFinaleLinks = [
    { name: "3-Min Demo", href: "/demo", icon: Play, highlight: true },
    { name: "ML Audit", href: "/model-performance", icon: BarChart3 },
    { name: "Jury Q&A", href: "/judge-qa", icon: HelpCircle },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-950/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-red-600/20 border border-red-500/40 flex items-center justify-center text-red-400">
              <Radar className="w-5 h-5 animate-spin text-red-500" style={{ animationDuration: '6s' }} />
            </div>
            <div>
              <Link href="/dashboard" className="flex items-center space-x-2">
                <span className="text-xl font-black tracking-wider text-white">
                  CYCLONE<span className="text-red-500">X</span>
                </span>
              </Link>
              <div className="text-[10px] uppercase font-mono tracking-widest text-slate-400">
                Early Warning & Decision Support
              </div>
            </div>
          </div>

          {/* Core Nav links */}
          <nav className="hidden xl:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-red-500/10 text-red-400 border border-red-500/30"
                      : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Grand Finale / SIH Judge Links */}
          <div className="flex items-center space-x-2">
            {grandFinaleLinks.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
                    item.highlight
                      ? isActive
                        ? "bg-amber-500 text-slate-950 shadow-lg shadow-amber-500/20 font-bold"
                        : "bg-amber-500/20 text-amber-300 border border-amber-500/50 hover:bg-amber-500/30"
                      : isActive
                        ? "bg-blue-600/20 text-blue-400 border border-blue-500/40"
                        : "bg-slate-900 border border-slate-700/60 text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.name}</span>
                </Link>
              );
            })}

            <div className="hidden sm:flex items-center space-x-1.5 pl-2 border-l border-slate-800 text-xs text-emerald-400 font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <span className="hidden md:inline">SYSTEM ONLINE</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

