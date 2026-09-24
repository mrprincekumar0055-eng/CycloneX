# CycloneX Master Model & System Status Registry

**Registry Version**: 3.0 (Forensically Verified)  
**Last Evaluation Run**: September 2026  
**Standards Body**: CycloneX Core MLOps & SIH Engineering Team  

---

## 1. Single Truth Model Status Table

| Component | Current Implementation | Trained? | Validation | Real Data? | Limitation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cyclone Classification** | `RandomForestClassifier` (100 trees, max_depth=5) | **YES** (`ml/artifacts/classifier_baseline.joblib`) | **Leave-One-Storm-Out (LOSO)**: 67.21% Accuracy, 0.6706 Weighted F1, 68.80% Balanced Acc (247 out-of-fold samples across 11 storms) | **YES** (NOAA NCEI IBTrACS v04r00 North Indian Ocean 6-hourly best-track dataset) | Predicts $T+6\text{h}$ category; does not predict intensity beyond 6 hours (intensity regressor handles longer horizons). |
| **Intensity Prediction** | `GradientBoostingRegressor` (80 trees, max_depth=3, lr=0.05) | **YES** (`ml/artifacts/intensity_baseline.joblib`) | **Leave-One-Storm-Out (LOSO)**:<br>• +6h: MAE = 6.32 kts (+14.6% skill)<br>• +12h: MAE = 10.21 kts (+27.7% skill)<br>• +24h: MAE = 18.40 kts (+30.9% skill)<br>• +48h: MAE = 29.96 kts (+32.0% skill)<br>• +72h: MAE = 40.70 kts (+17.2% skill) | **YES** (NOAA IBTrACS v04r00 6-hourly observations; 247 to 133 valid sequential pairs) | Evaluated on 11 historical North Indian Ocean storms; does not currently ingest real-time 3D atmospheric soundings. |
| **Track Prediction (CLIPER)** | Dual `GradientBoostingRegressor` (Displacement $\Delta \text{lat}, \Delta \text{lon}$) | **YES** (`ml/artifacts/track_*_baseline.joblib`) | **Leave-One-Storm-Out (LOSO)**:<br>• +6h: Mean Error = 41.3 km (Median: 34.5 km)<br>• +12h: Mean Error = 75.2 km (Median: 67.1 km)<br>• +24h: Mean Error = 141.9 km (Median: 131.5 km)<br>• +48h: Mean Error = 284.6 km (+5.8% skill)<br>• +72h: Mean Error = 388.8 km (+17.9% skill) | **YES** (NOAA IBTrACS v04r00 6-hourly observations; 1,000 auditable predictions exported) | Statistical-climatological kinematic regressor; does not run dynamic numerical weather prediction (NWP) primitive equations. |
| **Satellite Detection** | 8-Stage Image Pipeline (`ml/satellite_detector.py`) with Spectral-Gradient Vorticity & Eye Localization | **BASELINE ACTIVE**<br>(Deep CNN: **NOT TRAINED — DATASET REQUIRED**) | Functional pipeline quality checked on NASA GIBS WMTS tiles; eye candidate localization functional | **YES** (NASA GIBS WMTS tile endpoints active; synthetic vortex tiles fallback) | Deep Convolutional Neural Network / Vision Transformer weights are NOT trained; requires terabyte-scale INSAT-3D/HIMAWARI NetCDF4 corpus. |
| **Meteorological Detection** | `RandomForestClassifier` (50 trees, max_depth=4) | **YES** | Out-of-sample stratified split: 95.0% Accuracy, 0.942 F1 | **CALIBRATED** (Bounded meteorological distributions for vorticity, MSLP, shear, and SST) | Prototype meteorological disturbance classifier; flags cyclonic vs non-cyclonic atmospheric states. |
| **Risk Engine** | Multi-Criteria Weighted UNDRR Disaster Formulation (`Hazard × Exposure × Vulnerability × Uncertainty`) | **DETERMINISTIC FORMULATION** (Not an ML model) | Verified via boundary-condition unit tests, sensitivity tests, and spatial tests (`tests/test_geospatial.py`, `tests/test_risk_robustness.py`) | **YES** (Ingests Open-Meteo wind/pressure, WorldPop demographics, OSM coastal infrastructure) | Rapid decision-support triage index; does NOT execute numerical hydrodynamic shallow-water storm surge simulations. |
| **Location Intelligence** | Haversine distance, Holland vortex wind proxy, OSM facility discovery, OSRM road corridor planning | **DETERMINISTIC PIPELINE** | Verified across multiple coordinates (near eye, coastal, inland, arbitrary pairs) (`tests/test_location_intelligence.py`) | **YES** (OSM Overpass shelters and hospitals, OSRM road routing) | Optimal distance routing corridors; does not replace official Police / District Magistrate declared emergency evacuation routes. |

---

## 2. Integrity Commitments

1. No metric in this table was generated using duplicate synthetic samples.
2. Every ML metric is derived from genuine out-of-fold evaluations during Leave-One-Storm-Out cross-validation across 11 historical North Indian Ocean cyclones.
3. Satellite vision deep learning is explicitly designated as `NOT TRAINED — DATASET REQUIRED` until genuine satellite image model weights are trained on verified multi-spectral imagery.

