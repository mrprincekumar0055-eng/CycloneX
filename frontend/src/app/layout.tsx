import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import TopHeader from "@/components/TopHeader";

export const metadata: Metadata = {
  title: "CycloneX — Operational Tropical Cyclone Monitoring",
  description: "Operational tropical cyclone detection, track/intensity forecasting, risk intelligence, and evacuation decision support.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
      </head>
      <body className="min-h-screen bg-[#F6F7F9] text-slate-900 flex flex-row antialiased">
        {/* Left Fixed Navigation Sidebar */}
        <Sidebar />

        {/* Main Content Workspace */}
        <div className="main-content-workspace flex-1 flex flex-col min-w-0 min-h-screen ml-0 md:ml-[240px]">
          <TopHeader />
          <main className="flex-1 flex flex-col">
            {children}
          </main>
          <footer className="border-t border-slate-200 bg-white py-3 px-6 text-center text-[11px] text-slate-400 font-mono">
            CycloneX Operational Control Room • SIH26070 Solution • Data Sources: IMD, NOAA IBTrACS, NASA GIBS, Open-Meteo, WorldPop, OSM
          </footer>
        </div>
      </body>
    </html>
  );
}
