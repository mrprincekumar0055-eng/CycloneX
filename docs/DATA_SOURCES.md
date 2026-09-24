# CycloneX Data Sources & Ingestion Specifications

**Document Version**: 2.0 (SIH-Hardened)  
**Classification**: Engineering & Scientific Reference  
**Standard**: CycloneX Multi-Source Ingestion & Provenance Envelope Protocol

---

## 1. Architecture Overview

CycloneX ingests multi-source meteorological, oceanic, GIS, and demographic data across 6 primary external adapters. Every adapter inherits from `BaseDataAdapter` (`data/adapters/base.py`) guaranteeing:
1. **Contract Enforcing Lifecycle**: `fetch()` $\rightarrow$ `validate()` $\rightarrow$ `normalize()` $\rightarrow$ `timestamp()` $\rightarrow$ `source_status()`.
2. **Provenance Envelope**: Every record carries:
   - `source_name`: String identifier (e.g., `NOAA_IBTRACS_V04R00`, `NASA_GIBS_WMTS`).
   - `retrieval_timestamp`: UTC ISO-8601 string.
   - `data_status`: `LIVE`, `FALLBACK_CACHED`, or `SYNTHETIC_BENCHMARK`.
   - `quality_flag`: `NOMINAL`, `DEGRADED`, or `SIMULATED`.
   - `spatial_bounds`: Bounding box or coordinate reference point.
3. **Resilient Offline Fallback**: Under network failure, timeouts, or rate limits, the adapter automatically switches to verified offline catalogs without throwing unhandled exceptions.

---

## 2. Ingestion Adapters Matrix

| Source | Provider | Ingested Parameters | Live Endpoint | Update Frequency | Offline Fallback Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NOAA IBTrACS v04r00** | NOAA NCEI | 6-hourly best-track coordinates, $V_{max}$ (kts), $P_{min}$ (hPa), storm category, nature of storm | `https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r00/access/csv/ibtracs.NI.list.v04r00.csv` | Every 6 hours during operational season | Curated North Indian Ocean historical catalog (11 verified storms, 47 transitions: Biparjoy, Amphan, Tauktae, Fani, Mocha, etc.) |
| **NASA GIBS** | NASA Earthdata | Multi-spectral corrected reflectance imagery (MODIS Terra, Aqua, VIIRS SNPP) | `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/wmts.cgi` | 1-2 passes daily (real-time tiles within 3 hours) | Synthetic 256x256 test tiles with calibrated cyclonic vortex texture pattern |
| **Open-Meteo NWP** | Open-Meteo / ECMWF / DWD | 10m wind speed, wind gusts, mean sea level pressure (MSLP), relative humidity, precipitation | `https://api.open-meteo.com/v1/forecast` | Hourly updates / 3-hour forecasts | Climatological baseline distributions bounded to cyclone meteorological bounds |
| **OSM Overpass API** | OpenStreetMap Community | Evacuation shelters, emergency hospitals, critical ports, highway bridges | `https://overpass-api.de/api/interpreter` | Dynamic spatial query (On-Demand) | Curated coastal shelter database (GSDMA / OSDMA verified emergency cyclone shelters) |
| **OSRM Routing** | OpenStreetMap / OSRM Project | Multi-modal driving corridors, route distance (km), travel duration (min), turn-by-turn geometry | `http://router.project-osrm.org/route/v1/driving` | Dynamic calculation (On-Demand) | Geodesic great-circle coastal evacuation corridors |
| **WorldPop Gridded** | WorldPop / Univ. of Southampton | High-resolution gridded coastal population density (100m grid cell) | `https://hub.worldpop.org/rest/data/pop/wpgp` | Annual census / UN-adjusted projections | Calibrated 100m coastal density distributions for Gujarat, Odisha, and West Bengal corridors |

---

## 3. Data Normalization & Schemas

### 3.1 Meteorological & Best-Track Schema (`CycloneObservation`)
```json
{
  "timestamp": "2023-06-12T12:00:00Z",
  "latitude": 20.8,
  "longitude": 67.3,
  "wind_speed_kts": 85.0,
  "pressure_hpa": 964.0,
  "category": "Very Severe Cyclonic Storm",
  "data_provenance": {
    "source": "NOAA_IBTRACS_V04R00",
    "retrieval_timestamp": "2026-09-16T13:40:00Z",
    "data_status": "LIVE",
    "quality_flag": "NOMINAL"
  }
}
```

### 3.2 Facilities Schema (`EmergencyFacility`)
```json
{
  "id": "osm-node-102934",
  "name": "Mandvi Multipurpose Cyclone Shelter",
  "facility_type": "cyclone_shelter",
  "latitude": 22.82,
  "longitude": 69.34,
  "capacity": 1500,
  "status": "OPERATIONAL",
  "verified_by_authority": true,
  "data_provenance": {
    "source": "OSM_OVERPASS_API",
    "data_status": "LIVE"
  }
}
```

---

## 4. Operational Latencies & Resiliency Rules

1. **Timeout Threshold**: All external HTTP requests enforce an explicit `timeout=5.0` (or `8.0` for large queries) second hard cap.
2. **Circuit Breaker**: If 3 consecutive requests to an external API fail or time out:
   - The adapter switches to `FALLBACK_CACHED` mode.
   - Response payloads explicitly flag `"data_status": "FALLBACK_CACHED"` and `"degraded": true`.
   - The user interface displays a visible `[DEMO MODE]` or `[FALLBACK]` badge.
3. **Data Freshness Guarantee**: Telemetry is tagged with precise UTC timestamps. If live data age exceeds 6 hours, the system signals `STALE_TELEMETRY` advisory.

---

## 5. Official Authority Boundary & Disclaimer

CycloneX data ingestion pipelines are configured for **decision-support and situational awareness**. They do not usurp or replace official statutory bulletins from:
- **India Meteorological Department (IMD)**: The sole statutory authority for official cyclone categorization, landfall timing, and coastal storm surge warnings in the North Indian Ocean.
- **National Disaster Management Authority (NDMA) & State Disaster Management Authorities (SDMA)**: Statutory authorities for official evacuation mandates, shelter dispatch orders, and emergency relief operations.

