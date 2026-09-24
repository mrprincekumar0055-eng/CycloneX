import pytest
from ml.models.detector import CycloneDetector
from ml.models.classifier import CycloneClassifier
from ml.models.intensity import IntensityPredictor
from ml.models.track import TrackPredictor
from ml.explainability import CycloneExplainer
from ml.pipeline import ml_pipeline

def test_cyclone_detection():
    detector = CycloneDetector()
    # High cyclone probability scenario
    is_cyc, prob, metrics = detector.detect({
        "central_pressure_deficit": 35.0,
        "max_wind_kts": 85.0,
        "sst_c": 30.5,
        "wind_shear_kts": 8.0,
        "relative_humidity_pct": 88.0,
        "cloud_top_temp_c": -78.0
    })
    assert is_cyc is True
    assert prob >= 0.5
    assert metrics["f1_score"] > 0.8

def test_cyclone_classification_imd():
    # 85 kts corresponds to VSCS (Very Severe Cyclonic Storm)
    res = CycloneClassifier.classify_imd(85.0)
    assert res["imd_code"] == "VSCS"
    assert res["imd_label"] == "Very Severe Cyclonic Storm"
    assert "saffir_simpson" in res
    assert res["wind_speed_kmh"] == round(85.0 * 1.852, 1)

def test_intensity_forecasting():
    predictor = IntensityPredictor()
    forecasts = predictor.forecast_intensity(
        current_wind_kts=85.0,
        current_pressure_hpa=964.0,
        sst_c=30.0,
        wind_shear_kts=9.0
    )
    assert len(forecasts) == 5 # 6, 12, 24, 48, 72h
    for f in forecasts:
        assert f["predicted_wind_speed_kts"] > 0
        assert f["predicted_pressure_hpa"] > 900
        assert f["confidence_score"] > 0.5

def test_track_forecasting():
    predictor = TrackPredictor()
    track = predictor.predict_track(
        current_lat=21.65,
        current_lon=66.85,
        heading_deg=38.0,
        speed_kmh=11.5
    )
    assert len(track) == 5
    for pt in track:
        assert 10 <= pt["lat"] <= 35
        assert 50 <= pt["lon"] <= 85
        assert pt["uncertainty_radius_km"] >= 30.0

def test_full_ml_pipeline():
    inference = ml_pipeline.run_full_inference(
        cyclone_id="test-cyclone",
        current_lat=21.65,
        current_lon=66.85,
        current_wind_kts=85.0,
        current_pressure_hpa=964.0,
        current_heading_deg=38.0,
        current_speed_kmh=11.5
    )
    assert inference["detection"]["detected"] is True
    assert len(inference["forecast_points"]) == 5
    assert len(inference["explanation"]["bullet_points"]) > 0

