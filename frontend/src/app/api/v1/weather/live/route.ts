import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

// High-priority Indian Coastal & Maritime Monitoring Stations
const INDIA_GRID_STATIONS = [
  { id: "BOM", name: "Mumbai (Colaba / Coastal)", state: "Maharashtra", lat: 18.9067, lon: 72.8147 },
  { id: "GOA", name: "Panaji / Mormugao Port", state: "Goa", lat: 15.4989, lon: 73.8278 },
  { id: "IXE", name: "Mangalore Harbour", state: "Karnataka", lat: 12.9141, lon: 74.8560 },
  { id: "COK", name: "Kochi Marine Sector", state: "Kerala", lat: 9.9312, lon: 76.2673 },
  { id: "MAA", name: "Chennai Port / Coastal", state: "Tamil Nadu", lat: 13.0827, lon: 80.2707 },
  { id: "VTZ", name: "Visakhapatnam Outer Port", state: "Andhra Pradesh", lat: 17.6868, lon: 83.2185 },
  { id: "PBD", name: "Paradip Port Track", state: "Odisha", lat: 20.3167, lon: 86.6111 },
  { id: "CCU", name: "Kolkata / Haldia Port", state: "West Bengal", lat: 22.0250, lon: 88.0583 },
  { id: "DWK", name: "Dwarka Coastal Station", state: "Gujarat", lat: 22.2442, lon: 68.9685 },
  { id: "PBR", name: "Porbandar Coastal Outpost", state: "Gujarat", lat: 21.6417, lon: 69.6293 },
  { id: "VRL", name: "Veraval / Somnath Coast", state: "Gujarat", lat: 20.9000, lon: 70.3667 },
  { id: "IXZ", name: "Port Blair Marine Sector", state: "Andaman & Nicobar", lat: 11.6234, lon: 92.7265 },
  { id: "BIP", name: "Biparjoy Marine Reference", state: "Arabian Sea", lat: 21.6500, lon: 66.8500 }
];

const WMO_WEATHER_CODES: Record<number, string> = {
  0: "Clear sky",
  1: "Mainly clear",
  2: "Partly cloudy",
  3: "Overcast",
  45: "Fog",
  48: "Depositing rime fog",
  51: "Light drizzle",
  53: "Moderate drizzle",
  55: "Dense drizzle",
  61: "Slight rain",
  63: "Moderate rain",
  65: "Heavy rain",
  67: "Heavy freezing rain",
  71: "Slight snow",
  80: "Slight rain showers",
  81: "Moderate rain showers",
  82: "Violent rain showers",
  95: "Thunderstorm",
  96: "Thunderstorm with slight hail",
  99: "Thunderstorm with heavy hail"
};

// In-memory cache for resilient fallback
let lastKnownGoodData: Record<string, any> = {};

function calculateDisturbanceScore(windKts: number, gustKts: number, slpHpa: number, precipMm: number): number {
  const windPart = Math.min(45, (windKts / 64) * 45);
  const gustPart = Math.min(25, (gustKts / 80) * 25);
  const pressDeficit = Math.max(0, 1013 - slpHpa);
  const pressPart = Math.min(20, (pressDeficit / 30) * 20);
  const rainPart = Math.min(10, (precipMm / 25) * 10);
  return Math.round(Math.min(100, Math.max(0, windPart + gustPart + pressPart + rainPart)) * 10) / 10;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const target = searchParams.get("target") || "most_disturbed";
  const latStr = searchParams.get("lat");
  const lonStr = searchParams.get("lon");
  const refresh = searchParams.get("refresh") === "true";

  // 1. Try public FastAPI backend if BACKEND_URL is configured
  const backendBaseUrl = process.env.BACKEND_URL;
  if (backendBaseUrl) {
    try {
      const bUrl = backendBaseUrl.replace(/\/+$/, "");
      const destUrl = `${bUrl}/api/v1/weather/live?${searchParams.toString()}`;
      const backendRes = await fetch(destUrl, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal: AbortSignal.timeout(6000), // 6s timeout
      });

      if (backendRes.ok) {
        const data = await backendRes.json();
        lastKnownGoodData[target] = data;
        return NextResponse.json(data, {
          status: 200,
          headers: {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Data-Source": "FastAPI-Backend",
            "X-Backend-URL": bUrl
          }
        });
      }
    } catch {
      // Backend unavailable or timed out; proceed to resilient Open-Meteo direct fetch
    }
  }

  // 2. Direct Open-Meteo Ingestion (Edge Fallback & Standalone Provider)
  try {
    let targetStation: (typeof INDIA_GRID_STATIONS)[0];
    let queryLats: number[];
    let queryLons: number[];

    if (latStr && lonStr) {
      const parsedLat = parseFloat(latStr);
      const parsedLon = parseFloat(lonStr);
      targetStation = {
        id: "COORD",
        name: "Geospatial Inspection Point",
        state: "Indian Sector",
        lat: parsedLat,
        lon: parsedLon
      };
      queryLats = [parsedLat];
      queryLons = [parsedLon];
    } else if (target === "biparjoy") {
      targetStation = INDIA_GRID_STATIONS.find(s => s.id === "BIP") || INDIA_GRID_STATIONS[0];
      queryLats = [targetStation.lat];
      queryLons = [targetStation.lon];
    } else {
      // Batch query all Indian coastal grid stations
      queryLats = INDIA_GRID_STATIONS.map(s => s.lat);
      queryLons = INDIA_GRID_STATIONS.map(s => s.lon);
      targetStation = INDIA_GRID_STATIONS[0];
    }

    const openMeteoUrl = new URL("https://api.open-meteo.com/v1/forecast");
    openMeteoUrl.searchParams.set("latitude", queryLats.join(","));
    openMeteoUrl.searchParams.set("longitude", queryLons.join(","));
    openMeteoUrl.searchParams.set(
      "current",
      "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,surface_pressure,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover"
    );
    openMeteoUrl.searchParams.set("wind_speed_unit", "kn");
    openMeteoUrl.searchParams.set("timezone", "UTC");

    const omRes = await fetch(openMeteoUrl.toString(), {
      cache: "no-store",
      signal: AbortSignal.timeout(7000),
      headers: {
        "User-Agent": "CycloneX-EarlyWarning/1.0 (contact@cyclonex.gov.in)"
      }
    });

    if (!omRes.ok) {
      throw new Error(`Open-Meteo returned status ${omRes.status}`);
    }

    const omData = await omRes.json();
    const omList = Array.isArray(omData) ? omData : [omData];

    let bestStation = targetStation;
    let bestCurrent = omList[0]?.current || {};
    let maxDisturbance = -1;
    let bestRank = 1;

    // Evaluate disturbance for batch grid
    if (queryLats.length > 1) {
      const evaluated = omList.map((entry: any, idx: number) => {
        const cur = entry?.current || {};
        const wind = Number(cur.wind_speed_10m || 10);
        const gust = Number(cur.wind_gusts_10m || wind * 1.25);
        const slp = Number(cur.pressure_msl || cur.surface_pressure || 1012);
        const precip = Number(cur.precipitation || 0);
        const score = calculateDisturbanceScore(wind, gust, slp, precip);
        return {
          station: INDIA_GRID_STATIONS[idx],
          current: cur,
          score
        };
      });

      evaluated.sort((a, b) => b.score - a.score);
      bestStation = evaluated[0].station;
      bestCurrent = evaluated[0].current;
      maxDisturbance = evaluated[0].score;
      bestRank = 1;
    } else {
      const cur = bestCurrent;
      const wind = Number(cur.wind_speed_10m || 10);
      const gust = Number(cur.wind_gusts_10m || wind * 1.25);
      const slp = Number(cur.pressure_msl || cur.surface_pressure || 1012);
      const precip = Number(cur.precipitation || 0);
      maxDisturbance = calculateDisturbanceScore(wind, gust, slp, precip);
    }

    const windKts = Math.round(Number(bestCurrent.wind_speed_10m ?? 12) * 10) / 10;
    const windDeg = Math.round(Number(bestCurrent.wind_direction_10m ?? 0));
    const gustKts = Math.round(Number(bestCurrent.wind_gusts_10m ?? windKts * 1.25) * 10) / 10;
    const surfPressure = Math.round(Number(bestCurrent.surface_pressure ?? 1010) * 10) / 10;
    const slpHpa = Math.round(Number(bestCurrent.pressure_msl ?? surfPressure) * 10) / 10;
    const precipMm = Math.round(Number(bestCurrent.precipitation ?? 0) * 10) / 10;
    const tempC = Math.round(Number(bestCurrent.temperature_2m ?? 28) * 10) / 10;
    const rhPct = Math.round(Number(bestCurrent.relative_humidity_2m ?? 75));
    const cloudCover = Math.round(Number(bestCurrent.cloud_cover ?? 20));
    const weatherCode = Number(bestCurrent.weather_code ?? 0);
    const weatherCondition = WMO_WEATHER_CODES[weatherCode] || "Fair / Variable";
    const obsTimeIso = bestCurrent.time ? (bestCurrent.time.endsWith("Z") ? bestCurrent.time : `${bestCurrent.time}Z`) : new Date().toISOString();
    const nowIso = new Date().toISOString();

    const responsePayload = {
      status: "LIVE",
      data_status: "LIVE",
      source: "Open-Meteo NWP API",
      provider: "Open-Meteo",
      target,
      id: bestStation.id,
      name: bestStation.name,
      state: bestStation.state,
      latitude: bestStation.lat,
      longitude: bestStation.lon,
      disturbance_score: maxDisturbance,
      rank: bestRank,
      observation_time: obsTimeIso,
      timestamp: obsTimeIso,
      fetched_at: nowIso,
      last_sync_utc: nowIso,
      freshness_seconds: 0,
      surface_wind_10m_kts: windKts,
      wind_direction_10m_deg: windDeg,
      wind_gust_kts: gustKts,
      weather_condition: weatherCondition,
      sea_level_pressure_hpa: slpHpa,
      precipitation_mm: precipMm,
      air_temperature_2m_c: tempC,
      relative_humidity_pct: rhPct,
      cloud_cover_pct: cloudCover,
      weather_code: weatherCode,
      weather: {
        temperature_c: tempC,
        wind_speed_kts: windKts,
        wind_direction_deg: windDeg,
        wind_gust_kts: gustKts,
        surface_pressure_hpa: surfPressure,
        sea_level_pressure_hpa: slpHpa,
        precipitation_mm: precipMm,
        relative_humidity_pct: rhPct,
        cloud_cover_pct: cloudCover,
        weather_condition: weatherCondition,
        weather_code: weatherCode
      },
      location: {
        nearest_grid_station: bestStation.name,
        name: bestStation.name,
        state: bestStation.state,
        distance_to_station_km: 0
      }
    };

    lastKnownGoodData[target] = responsePayload;

    return NextResponse.json(responsePayload, {
      status: 200,
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "X-Data-Source": "Open-Meteo-Live"
      }
    });
  } catch (error: any) {
    // 3. Fallback to STALE cache if available
    const staleData = lastKnownGoodData[target];
    if (staleData) {
      return NextResponse.json(
        {
          ...staleData,
          status: "STALE",
          data_status: "STALE",
          cached_at: staleData.fetched_at || staleData.observation_time
        },
        {
          status: 200,
          headers: {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Data-Source": "Memory-Cache-Stale"
          }
        }
      );
    }

    // 4. Fallback to OFFLINE if no cache and provider unreachable
    return NextResponse.json(
      {
        status: "OFFLINE",
        data_status: "OFFLINE",
        source: "Open-Meteo NWP API",
        error: error?.message || "Failed to reach weather provider",
        timestamp: new Date().toISOString()
      },
      {
        status: 200, // Return 200 so UI can cleanly parse OFFLINE state without network exception
        headers: {
          "Cache-Control": "no-cache, no-store, must-revalidate"
        }
      }
    );
  }
}
