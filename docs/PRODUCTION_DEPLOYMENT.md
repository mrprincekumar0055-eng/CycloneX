# CycloneX Production Deployment & Architecture Guide

## 1. Production Architecture Overview

```
                      +-------------------------------+
                      |          Public User          |
                      +---------------+---------------+
                                      |
                                      v HTTPS
                      +-------------------------------+
                      |   Vercel Next.js Frontend    |
                      |  https://cyclone-x-hro.       |
                      |          vercel.app           |
                      +---------------+---------------+
                                      |
                                      | HTTPS (Centralized Client via
                                      | NEXT_PUBLIC_API_BASE_URL)
                                      v
                      +-------------------------------+
                      |   FastAPI Production Backend  |
                      | (Render / Railway / Cloud Run)|
                      +---------------+---------------+
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
         v                            v                            v
+------------------+         +------------------+         +------------------+
|   SQLite / PG    |         |   Live In-Memory |         | Real External    |
|   Database       |         |   Weather Cache  |         | Providers        |
| (cyclonex.db)    |         | (44-Station Grid)|         | - Open-Meteo     |
+------------------+         +------------------+         | - NOAA IBTrACS   |
                                                          | - NASA GIBS      |
                                                          | - WorldPop       |
                                                          | - OSM / OSRM     |
                                                          +------------------+
```

---

## 2. Root Cause Analysis: Why Modules Showed "API Unreachable"

| Module | Observed Error | Root Cause | Architectural Fix |
|---|---|---|---|
| **Dashboard** | `Weather service offline. Weather service unreachable.` | Next.js rewrote to `http://127.0.0.1:8000` because `BACKEND_URL` was unset in Vercel. Browser then tried localhost on the visitor's machine. | Centralized API client in `frontend/src/lib/api.ts` targets `NEXT_PUBLIC_API_BASE_URL`. Never queries localhost in production. |
| **Risk** | `Offline Mode: Risk engine API unreachable.` | `fetchFromAPI("/cyclones/1/risk")` failed because no public FastAPI instance was running. | Centralized API client routes all risk requests to the public backend domain. |
| **Evacuation** | `Offline Mode: Logistics API unreachable.` | `fetchFromAPI("/facilities/shelters")` and `/routes` failed due to absent public backend. | Configured logistics routes to resolve to public backend. |
| **Alerts** | `Offline Mode: Alert dispatch service unreachable.` | `fetchFromAPI("/alerts")` and `/alerts/config` failed due to absent public backend. | Connected to public backend alerts router. |
| **TopHeader** | `SYSTEM: Operational` contradiction | Initialized state to `true` and lacked a multi-service status evaluation. | Added multi-service health checker and interactive **Production Services Status Panel**. |

---

## 3. Persistent Backend Deployment (Render / Railway)

The FastAPI backend must run on an independent cloud server so it works **even when your local PC is switched off**.

### Option A: Render (Recommended — Simplest Free/Low-Cost Setup)
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New + → Web Service**.
2. Connect your GitHub repository: `https://github.com/mrprincekumar0055-eng/CycloneX`.
3. Set the following build and start commands:
   - **Name:** `cyclonex-api`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
4. Add the **Backend Environment Variables** (see Section 5 below).
5. Deploy. Render assigns a public HTTPS URL:
   `https://cyclonex-api.onrender.com`

### Option B: Railway
1. Go to [Railway Dashboard](https://railway.app/) and click **New Project → Deploy from GitHub repo**.
2. Select `mrprincekumar0055-eng/CycloneX`.
3. Railway automatically detects `Procfile` or `Dockerfile`:
   `web: uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
4. Add environment variables and click **Generate Domain**.

---

## 4. Vercel Environment Variables Configuration

In your **Vercel Project Dashboard** (`https://vercel.com/` → Project Settings → **Environment Variables**):

| Variable Name | Value | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://cyclonex-api.onrender.com` | Primary public API URL for all frontend browser calls |
| `BACKEND_URL` | `https://cyclonex-api.onrender.com` | Server-side runtime proxy URL for Next.js SSR and rewrites |

> [!IMPORTANT]
> Once you set `NEXT_PUBLIC_API_BASE_URL` in Vercel, trigger a **Redeploy** on Vercel so the environment variable is baked into the frontend build.

---

## 5. Backend Environment Variables (Render / Railway / .env)

```env
PROJECT_NAME="CycloneX"
ENVIRONMENT="production"
PORT=8000
API_V1_STR="/api/v1"
SECRET_KEY="cyclonex-super-secret-production-key-change-in-prod"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL="sqlite:///./cyclonex.db"

# CORS (Allowed Origins for Vercel)
BACKEND_CORS_ORIGINS="https://cyclone-x-hro.vercel.app,https://cyclone-x.vercel.app,http://localhost:3000"

# External APIs
OPEN_METEO_API_URL="https://api.open-meteo.com/v1"
NASA_GIBS_API_URL="https://gibs.earthdata.nasa.gov"
OVERPASS_API_URL="https://overpass-api.de/api/interpreter"
OSRM_API_URL="http://router.project-osrm.org"
WORLDPOP_API_URL="https://data.worldpop.org"

# Operational Mode
DEMO_MODE=true
ALLOW_SYNTHETIC_FALLBACK=true

# Notification & Alert Settings (Simulation Safe by Default)
LIVE_ALERTS_ENABLED=false
SMS_PROVIDER="mock"
EMAIL_PROVIDER="mock"
TEST_NOTIFICATION_PHONE="+91-98765-43210"
TEST_NOTIFICATION_EMAIL="admin@cyclonex.gov.in"
```

---

## 6. Health & Readiness Verification

Once the backend is deployed, verify it using these endpoints:

### Liveness Probe
```bash
curl -i https://<YOUR-BACKEND-DOMAIN>/health
```
**Expected Response (HTTP 200):**
```json
{
  "status": "ok",
  "service": "cyclonex-api",
  "version": "1.0.0",
  "timestamp": "2026-09-24T13:30:00Z"
}
```

### Readiness Probe
```bash
curl -i https://<YOUR-BACKEND-DOMAIN>/health/ready
```
**Expected Response (HTTP 200):**
```json
{
  "status": "ready",
  "service": "cyclonex-api",
  "database": "connected",
  "weather_cache_ready": true,
  "cached_stations": 44,
  "live_alerts_enabled": false
}
```

### Live Weather Ingestion Test
```bash
curl -i "https://<YOUR-BACKEND-DOMAIN>/api/v1/weather/live?lat=19.0760&lon=72.8777&refresh=true"
```
**Expected Response (HTTP 200):**
```json
{
  "status": "LIVE",
  "data_status": "LIVE",
  "source": "Open-Meteo NWP API",
  "weather": {
    "temperature_c": 28.2,
    "wind_speed_kts": 4.9,
    "weather_condition": "Overcast"
  }
}
```

---

## 7. Complete API Route Inventory

| Router Prefix | Method | Endpoint | Module | Purpose |
|---|---|---|---|---|
| Root | `GET` | `/health` | Core | Liveness health probe |
| Root | `GET` | `/health/ready` | Core | Readiness database & provider probe |
| `/api/v1/system` | `GET` | `/system/health` | Header/Admin | Database & active storm status |
| `/api/v1/system` | `GET` | `/system/data-sources` | Admin | Status & latency of 5 external providers |
| `/api/v1/weather` | `GET` | `/weather/live` | Dashboard | Real-time Open-Meteo observations |
| `/api/v1/weather` | `GET` | `/weather/most-disturbed` | Dashboard | Top meteorological disturbance point in India |
| `/api/v1/weather` | `GET` | `/weather/grid` | Dashboard | All-India 44-station synoptic grid |
| `/api/v1/cyclones`| `GET` | `/cyclones` | Catalog | Active & historical cyclone catalog |
| `/api/v1/cyclones`| `GET` | `/cyclones/{id}` | Catalog | Cyclone metadata & current intensity |
| `/api/v1/cyclones`| `GET` | `/cyclones/{id}/track` | Forecast | Track history coordinates & timestamps |
| `/api/v1/cyclones`| `GET` | `/cyclones/{id}/forecast` | Forecast | ML 24h/48h/72h trajectory & wind forecasts |
| `/api/v1/cyclones`| `GET` | `/cyclones/{id}/risk` | Risk | UNDRR risk score & vulnerability index |
| `/api/v1/cyclones`| `GET` | `/cyclones/{id}/exposure` | Exposure | Population swath & district exposure |
| `/api/v1/cyclones`| `GET` | `/cyclones/{id}/location-intelligence` | Dashboard | GIS coordinate dossier (distance, bearing, risk) |
| `/api/v1/facilities`| `GET` | `/facilities/shelters` | Evacuation | Disaster shelters & capacity |
| `/api/v1/facilities`| `GET` | `/facilities/hospitals` | Evacuation | Medical centers & bed availability |
| `/api/v1/routes` | `GET` | `/routes` | Evacuation | Evacuation corridors & travel duration |
| `/api/v1/alerts` | `GET` | `/alerts` | Alerts | Active alert inbox & authority directives |
| `/api/v1/alerts` | `GET` | `/alerts/stats` | Alerts | Summary alert counters (Red, Orange, Yellow) |
| `/api/v1/alerts` | `POST`| `/alerts/evaluate-now` | Alerts | Manual ML-to-alert evaluation trigger |
| `/api/v1/alerts` | `POST`| `/alerts/test-live-delivery` | Alerts | Controlled live delivery verification |
| `/api/v1/historical`| `GET` | `/historical/analogs` | Historical | NOAA IBTrACS analog storm search |

---

## 8. Graceful Degradation Matrix

| External Failure | Application Behavior | Visual Indicator |
|---|---|---|
| **Open-Meteo Temporarily Down** | Serves cached observations if available (`STALE`), or clearly signals `OFFLINE`. | Amber badge `STALE` or Rose badge `OFFLINE`. Never crashes dashboard. |
| **OSM / Map Tiles Slow** | Map layers render fallback vector basemap; logistics table continues functioning. | Map status shows ambient state. |
| **OSRM Routing Offline** | Corridors fall back to Haversine straight-line distance approximations. | Corridor status clearly notes offline routing proxy. |
| **Alert SMS/Email Down** | Alert records created in SQLite database; delivery status flagged `FAILED` / `PENDING`. | Audit log retains delivery attempts. |
| **Backend Unreachable** | Frontend displays truthful "Offline Mode" banners with cached local profiles. | Header displays `SYSTEM: Offline` with red pulsing indicator. |

---

## 9. Local Development Commands

To run CycloneX locally:

```bash
# 1. Start FastAPI backend (port 8000)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Start Next.js frontend (port 3000)
cd frontend
npm run dev
```

Visit: `http://localhost:3000/dashboard`
