# CycloneX — AI-Powered Tropical Cyclone Intelligence & Early Warning

> **SIH Problem Statement SIH26070**: AI/ML-based identification, classification and prediction of tropical cyclone patterns using multi-source satellite and meteorological data.

**CycloneX** is a full-lifecycle disaster intelligence and early warning decision-support platform executing:
$$\text{Detect} \longrightarrow \text{Classify} \longrightarrow \text{Predict} \longrightarrow \text{Assess Risk} \longrightarrow \text{Explain} \longrightarrow \text{Alert} \longrightarrow \text{Recommend Action}$$

---

## Architecture Overview

```text
                               ┌───────────────────────────────────────────────────────────┐
                               │                 CYCLONEX COMMAND CENTER                   │
                               │                Next.js (React / TS / Tailwind)            │
                               └─────────────────────────────┬─────────────────────────────┘
                                                             │ REST / Reverse Proxy
                               ┌─────────────────────────────▼─────────────────────────────┐
                               │                    FASTAPI BACKEND                        │
                               │  Auth (JWT/RBAC) · CORS · RateLimit · OpenAPI Docs         │
                               └──────┬──────────────────────┼──────────────────────┬──────┘
                                      │                      │                      │
                   ┌──────────────────▼──────┐    ┌──────────▼──────────┐   ┌───────▼─────────────────┐
                   │    AI/ML ENGINE         │    │    RISK ENGINE      │   │   ALERT & EVAC ENGINE   │
                   │ • Detection (RF/XGB)    │    │ Hazard × Exposure × │   │ • Multi-tier Alerts     │
                   │ • Intensity (6-72h reg) │    │ Vulnerability       │   │ • OSM Shelter Finder    │
                   │ • Track Prediction      │    │ Population Impact   │   │ • OSRM / Geodesic Route │
                   │ • Explainability (SHAP) │    │ Spatial Uncertainty │   │ • Role Action Engine    │
                   └──────────────────┬──────┘    └──────────┬──────────┘   └───────┬─────────────────┘
                                      │                      │                      │
                               ┌──────┴──────────────────────┴──────────────────────┴──────┐
                               │                   DATA ADAPTER LAYER                      │
                               │  • NOAA IBTrACS (Historical)  • NASA GIBS (Satellite)     │
                               │  • Open-Meteo (Weather/Ocean) • WorldPop (Demographics)   │
                               │  • Overpass API (OSM Assets)  • OSRM (Routing)            │
                               │  • Demo Fallback Provider (Offline / Resilient Demo)      │
                               └─────────────────────────────┬─────────────────────────────┘
                                                             │
                               ┌─────────────────────────────▼─────────────────────────────┐
                               │              DATA & STORAGE INFRASTRUCTURE                │
                               │   PostgreSQL 16 + PostGIS (Dual SQLite/Spatial fallback)   │
                               │   Redis Cache / In-Memory Cache · Background Tasks        │
                               └───────────────────────────────────────────────────────────┘
```

---

## Key Modules & Capabilities

1. **Live Command Center (`/dashboard`)**:
   - Real-time telemetry: wind speed, barometric pressure, IMD category, movement vector.
   - Tactical interactive map with multi-layer toggles: NASA GIBS satellite tiles, past track, forecast points, uncertainty envelope, 34/50/64-kt wind swaths, shelters, and evacuation route.
   - AI decision rationale box explaining environmental drivers (SST, shear, vorticity).
   - Role-targeted emergency alerts feed.
2. **Detection & Classification (`/cyclones`)**:
   - Random Forest detection classifier.
   - Official IMD (D, DD, CS, SCS, VSCS, ESCS, SuCS) and Saffir-Simpson category mapping.
3. **Intensity & Track Prediction (`/forecast`)**:
   - 6h, 12h, 24h, 48h, 72h lead-time forecasts for wind speed, pressure, and lat/lon coordinates.
   - Dynamic uncertainty cone expansion modeling.
4. **Risk Engine (`/risk`)**:
   - Quantitative disaster risk score: $\text{Hazard} \times \text{Exposure} \times \text{Vulnerability} \times \text{Uncertainty}$.
5. **Exposure Intelligence (`/exposure`)**:
   - Spatial overlap with WorldPop demographic densities to isolate vulnerable coastal segments.
6. **Shelters & Evacuation Routing (`/evacuation`)**:
   - Nearest shelter and trauma hospital search with route flood-risk assessment.
7. **Historical Analogs (`/historical`)**:
   - NOAA IBTrACS similarity matcher comparing track geometry and central pressure profiles.
8. **Multi-Stakeholder Alerts (`/alerts`)**:
   - Separate actionable guidance checklists for Citizens, District Authorities, and First Responders.
9. **System Administration & Health (`/admin`)**:
   - Health check endpoints (`/api/v1/system/health`), data source latency telemetry, and model registry metrics.

---

## Quickstart Guide

### 1. Backend Setup (FastAPI)
```bash
# In project root
python -m venv venv
venv\Scripts\activate      # Windows
# or: source venv/bin/activate # Linux/Mac

pip install -r backend/requirements.txt
pip install email-validator

# Seed database with initial benchmark models & demo data
python scripts/seed_demo_data.py

# Launch FastAPI backend on port 8000
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be accessible at `http://localhost:8000/docs`.

### 2. Frontend Setup (Next.js)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to access the Command Center.

> **Operational Rule**: Never run `npm run build` while `npm run dev` is active on the same port — kill dev first. (The `prebuild` hook automatically guards against this by checking port 3000).

### 3. Docker Deployment
```bash
docker compose up --build
```
Launches PostgreSQL 16 with PostGIS, Redis, FastAPI, and Next.js concurrently.

### 4. Running Automated Tests
```bash
python -m pytest tests/
```
Executes all 37 unit and integration tests across ML baselines, geospatial algorithms, UNDRR risk formulations, data adapters, location intelligence, and REST endpoints (37 passed, 0 failed).

---

## Scientific Validation & MLOps Standards

CycloneX adheres to strict scientific validation standards to eliminate synthetic metric inflation and data leakage:
- **Storm-Grouped Leave-One-Storm-Out (LOSO) Cross-Validation**: Evaluated across 11 historical North Indian Ocean cyclones using 258 6-hourly synoptic observations from NOAA IBTrACS v04r00. Prevents temporal and spatial data leakage by ensuring no training storm's observations cross into test folds.
- **T+6h Stage Classification**: Multi-class transition evaluated at 67.21% Accuracy and 0.6706 Weighted F1 across 6 IMD categories without access to future wind speeds (vs 21.46% majority class and 16.67% random baseline).
- **Persistence Baselines**: Intensity model achieves positive skill over persistence across all horizons: **+14.6% skill** at +6h (MAE: 6.32 kts vs 7.40 kts), **+27.7% skill** at +12h, **+30.9% skill** at +24h, **+32.0% skill** at +48h, and **+17.2% skill** at +72h. Track model achieves monotonic error scaling (41 km at +6h to 388 km at +72h) with positive skill at +48h (+5.8%) and +72h (+17.9%).
- **Satellite Vision**: Modular 8-stage image pipeline interface with analytic vorticity baseline; deep CNN backbones are explicitly documented as requiring terabyte-scale INSAT-3D/HIMAWARI datasets.

See [`docs/ML_REPRODUCIBILITY.md`](docs/ML_REPRODUCIBILITY.md), [`docs/MODEL_STATUS.md`](docs/MODEL_STATUS.md), [`docs/RISK_MODEL.md`](docs/RISK_MODEL.md), and [`docs/FINAL_SIH_READINESS.md`](docs/FINAL_SIH_READINESS.md) for full scientific reports.

