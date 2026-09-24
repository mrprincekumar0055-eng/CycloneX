import sys, os
sys.path.insert(0, os.path.abspath("."))
import urllib.request
import json
from ml.pipeline import ml_pipeline
from ml.models.detector import CycloneDetector
from ml.models.classifier import CycloneClassifier
from ml.models.intensity import IntensityPredictor
from ml.models.track import TrackPredictor
from geospatial.risk_engine import RiskEngine
import joblib
import os

print("=" * 80)
print("EXPERIMENT 1: Live API endpoint /cyclones/{id}/forecast with different cyclones")
print("=" * 80)
base = "http://127.0.0.1:8000/api/v1"

for cid in ['demo-biparjoy-2023', 'ibtracs-amphan-2020', 'ibtracs-mocha-2023', 'ibtracs-nisarga-2020']:
    url = f"{base}/cyclones/{cid}/forecast"
    with urllib.request.urlopen(url) as res:
        r = json.loads(res.read().decode('utf-8'))
        fp0 = r['forecast_points'][0]
        fp_last = r['forecast_points'][-1]
        print(f"Cyclone: {cid}")
        print(f"  +6h:  Lat {fp0['lat']}, Lon {fp0['lon']}, Wind {fp0['predicted_wind_speed_kts']} kts, Cat {fp0['category']}")
        print(f"  +72h: Lat {fp_last['lat']}, Lon {fp_last['lon']}, Wind {fp_last['predicted_wind_speed_kts']} kts, Cat {fp_last['category']}")

print("\n" + "=" * 80)
print("EXPERIMENT 2: Live Location-Specific Intelligence Endpoint with varying Lat/Lon inputs")
print("=" * 80)
# Testing /cyclones/demo-biparjoy-2023/location-intelligence?lat=...&lon=...
coords = [
    (23.238, 68.618, "Jakhau Coast (Direct landfall proximity)"),
    (22.244, 68.968, "Dwarka (Southern flank)"),
    (24.500, 72.000, "Inland Rajasthan (Distant)"),
    (18.000, 72.800, "Mumbai (Distant South)")
]

for lat, lon, desc in coords:
    url = f"{base}/cyclones/demo-biparjoy-2023/location-intelligence?lat={lat}&lon={lon}"
    with urllib.request.urlopen(url) as res:
        r = json.loads(res.read().decode('utf-8'))
        ra = r['risk']
        print(f"Location: {desc} ({lat}N, {lon}E)")
        print(f"  Distance to Eye: {r['cyclone_distance_km']} km | Bearing: {r['bearing_deg']} deg | Local Wind: {r['local_estimated_wind_kts']} kts")
        print(f"  Risk Category: {ra['risk_category']} | Composite Risk: {ra['composite_risk_score']} (Hazard: {ra['hazard_score']}, Exposure: {ra['exposure_score']}, Vuln: {ra['vulnerability_score']})")
        print(f"  Nearest Shelter: {r['nearest_shelter']['name']} ({r['nearest_shelter']['distance_km']} km)")

print("\n" + "=" * 80)
print("EXPERIMENT 3: Direct Live ML Pipeline Inference with Varying Physical Parameters")
print("=" * 80)

# Varying wind speed and SST
cases = [
    {"name": "Severe Cyclone / Warm Ocean", "lat": 20.0, "lon": 65.0, "wind": 100.0, "press": 950.0, "sst": 31.0, "shear": 8.0},
    {"name": "Moderate Cyclone / Neutral Ocean", "lat": 18.0, "lon": 68.0, "wind": 50.0, "press": 990.0, "sst": 28.0, "shear": 15.0},
    {"name": "Weak Disturbance / High Shear", "lat": 15.0, "lon": 70.0, "wind": 25.0, "press": 1006.0, "sst": 26.0, "shear": 30.0},
]

for c in cases:
    res = ml_pipeline.run_full_inference(
        cyclone_id="dynamic-test",
        current_lat=c["lat"],
        current_lon=c["lon"],
        current_wind_kts=c["wind"],
        current_pressure_hpa=c["press"],
        current_heading_deg=35.0,
        current_speed_kmh=15.0,
        sst_c=c["sst"],
        wind_shear_kts=c["shear"]
    )
    det = res["detection"]
    cls = res["classification"]
    fp = res["forecast_points"]
    print(f"Case: {c['name']} (Wind: {c['wind']} kts, SST: {c['sst']}C, Shear: {c['shear']} kts)")
    print(f"  Detection Prob: {det['probability']:.3f} | Detected: {det['detected']} | Status: {det['status']}")
    print(f"  Classification: {cls['imd_label']} (Code: {cls['imd_code']})")
    print(f"  +6h Wind: {fp[0]['predicted_wind_speed_kts']} kts -> +72h Wind: {fp[-1]['predicted_wind_speed_kts']} kts")
    print(f"  +6h Pos: ({fp[0]['lat']}, {fp[0]['lon']}) -> +72h Pos: ({fp[-1]['lat']}, {fp[-1]['lon']})")

print("\n" + "=" * 80)
print("EXPERIMENT 4: Direct joblib Trained Scikit-Learn Model Inference (.predict)")
print("=" * 80)
clf_model = joblib.load("ml/artifacts/classifier_baseline.joblib")
intensity_model = joblib.load("ml/artifacts/intensity_baseline.joblib")
track_lat_model = joblib.load("ml/artifacts/track_dlat_baseline.joblib")
track_lon_model = joblib.load("ml/artifacts/track_dlon_baseline.joblib")

test_inputs = [
    # [lat, lon, wind_kts, pressure_hpa, pressure_deficit, d_lat_prev, d_lon_prev, d_wind_prev, trans_speed_kmh]
    [21.65, 66.85, 85.0, 964.0, 46.0, 0.8, 0.4, 5.0, 14.0],
    [15.20, 88.30, 130.0, 920.0, 90.0, 1.2, 0.6, 15.0, 20.0],
    [12.00, 68.00, 30.0, 1004.0, 6.0, 0.2, 0.1, 0.0, 8.0]
]

for idx, inp in enumerate(test_inputs):
    pred_cat = clf_model.predict([inp])[0]
    pred_int_6h = intensity_model.predict([inp])[0]
    # track uses 7 features: lat, lon, wind_kts, pressure_deficit, d_lat_prev, d_lon_prev, trans_speed_kmh
    track_inp = [inp[0], inp[1], inp[2], inp[4], inp[5], inp[6], inp[8]]
    pred_dlat = track_lat_model.predict([track_inp])[0]
    pred_dlon = track_lon_model.predict([track_inp])[0]
    print(f"Joblib Test Input #{idx+1} (Wind: {inp[2]} kts, Pres: {inp[3]} hPa, Deficit: {inp[4]} hPa):")
    print(f"  RandomForestClassifier.predict()   -> Stage T+6h: '{pred_cat}'")
    print(f"  GradientBoostingRegressor.predict()-> Wind T+6h:  {pred_int_6h:.2f} kts")
    print(f"  Track GBR Models .predict()        -> Delta Lat/Lon T+6h: ({pred_dlat:+.3f}, {pred_dlon:+.3f})")
