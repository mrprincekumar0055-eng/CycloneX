"""
Pre-Packaged SIH Demonstration Scenario: Cyclone Biparjoy
High-fidelity operational scenario for offline / infallible hackathon evaluation.
Clearly labeled as: DEMO DATA — VERIFIED HISTORICAL RE-RUN (NOT OPERATIONAL)
"""
from datetime import datetime, timezone, timedelta

DEMO_BIPARJOY = {
    "cyclone": {
        "id": "demo-biparjoy-2023",
        "name": "BIPARJOY",
        "basin": "Arabian Sea",
        "status": "active",
        "current_lat": 21.65,
        "current_lon": 66.85,
        "current_wind_speed_kts": 85.0, # 157 km/h - Very Severe Cyclonic Storm
        "current_pressure_hpa": 964.0,
        "current_category": "Very Severe Cyclonic Storm",
        "current_heading_deg": 38.0, # Northeast towards Saurashtra-Kutch
        "current_speed_kmh": 11.5,
        "confidence_score": 0.94,
        "risk_level": "Extreme Risk"
    },
    "environmental": {
        "sst_c": 30.2,
        "wind_shear_kts": 10.5,
        "cloud_top_temp_c": -78.5,
        "wave_height_m": 6.8
    },
    "historical_observations": [
        {"timestamp": "2023-06-12T00:00:00Z", "lat": 19.3, "lon": 67.7, "wind_speed_kts": 90, "central_pressure_hpa": 956, "imd_category": "ESCS"},
        {"timestamp": "2023-06-12T12:00:00Z", "lat": 19.9, "lon": 67.4, "wind_speed_kts": 90, "central_pressure_hpa": 958, "imd_category": "ESCS"},
        {"timestamp": "2023-06-13T00:00:00Z", "lat": 20.6, "lon": 67.1, "wind_speed_kts": 85, "central_pressure_hpa": 962, "imd_category": "VSCS"},
        {"timestamp": "2023-06-13T12:00:00Z", "lat": 21.2, "lon": 66.9, "wind_speed_kts": 85, "central_pressure_hpa": 964, "imd_category": "VSCS"},
        {"timestamp": "2023-06-14T00:00:00Z", "lat": 21.65, "lon": 66.85, "wind_speed_kts": 85, "central_pressure_hpa": 964, "imd_category": "VSCS"}
    ],
    "target_landfall": {
        "location": "Jakhau Port / Mandvi, Kutch District, Gujarat",
        "eta_hours": 24,
        "projected_landfall_time": "2023-06-15T12:30:00Z"
    }
}

