import os
import json
import pytest
import joblib
import numpy as np
from ml.vision_pipeline import satellite_vision_pipeline
from ml.explainability import CycloneExplainer

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "artifacts")

def test_ml_artifacts_exist():
    clf_path = os.path.join(ARTIFACTS_DIR, "classifier_baseline.joblib")
    reg_path = os.path.join(ARTIFACTS_DIR, "intensity_baseline.joblib")
    metrics_path = os.path.join(ARTIFACTS_DIR, "evaluation_metrics.json")
    
    assert os.path.exists(clf_path)
    assert os.path.exists(reg_path)
    assert os.path.exists(metrics_path)
    
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
    assert "classification_validation" in metrics or "classification" in metrics
    clf_metrics = metrics.get("classification_validation", metrics.get("classification", {}))
    assert clf_metrics["accuracy"] >= 0.50 # Leak-free LOSO accuracy
    assert "intensity_validation" in metrics or "intensity" in metrics
    assert "track_validation" in metrics or "track" in metrics
    if "intensity_validation" in metrics:
        assert metrics["intensity_validation"]["horizons"]["6h"]["skill_improvement_pct"] > 0
    if "track_validation" in metrics:
        assert metrics["track_validation"]["horizons"]["48h"]["skill_improvement_pct"] > 0
        assert metrics["track_validation"]["horizons"]["72h"]["skill_improvement_pct"] > 0

def test_loso_strict_no_storm_overlap():
    metrics_path = os.path.join(ARTIFACTS_DIR, "evaluation_metrics.json")
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
    
    assert "loso_folds" in metrics
    folds = metrics["loso_folds"]
    all_storms = metrics["dataset_summary"]["storms_included"]
    
    test_storms_seen = set()
    for fold in folds:
        test_storm = fold["test_storm"]
        # Test storm must not have been seen in prior test folds
        assert test_storm not in test_storms_seen, f"Storm {test_storm} duplicated in test folds"
        test_storms_seen.add(test_storm)
        # Training set count must equal total storms minus 1
        assert fold["train_storms_count"] == len(all_storms) - 1
    
    # Union of test storms must exactly match all storms
    assert test_storms_seen == set(all_storms)

def test_deterministic_baseline_inference():
    clf_path = os.path.join(ARTIFACTS_DIR, "classifier_baseline.joblib")
    clf = joblib.load(clf_path)
    
    # Feature vector: lat, lon, wind_kts, pressure_hpa, pressure_deficit, d_lat_prev, d_lon_prev, d_wind_prev, trans_speed_kmh
    x = np.array([[21.65, 66.85, 85.0, 964.0, 46.0, 0.45, -0.25, 0.0, 15.0]])
    pred1 = clf.predict(x)[0]
    pred2 = clf.predict(x)[0]
    assert pred1 == pred2 # Deterministic
    assert pred1 in ["Very Severe Cyclonic Storm", "Extremely Severe Cyclonic Storm"]

def test_satellite_vision_pipeline_interface():
    res = satellite_vision_pipeline.execute_pipeline(
        tile_url="https://gibs.earthdata.nasa.gov/wmts/tile.jpg",
        base_lat=21.65,
        base_lon=66.85
    )
    assert "pipeline_stages" in res
    assert len(res["pipeline_stages"]) == 6
    assert "primary_candidate" in res
    assert res["model_metadata"]["status"].startswith("HEURISTIC_SPECTRAL_BASELINE")

def test_explainability_grounded_attributions():
    explanation = CycloneExplainer.explain_prediction(
        sst_c=30.2,
        wind_shear_kts=10.0,
        central_pressure_deficit=46.0,
        wind_trend="Steady",
        proximity_to_coast_km=85.0,
        population_exposed=750000
    )
    assert "sst" in explanation["attribution_weights"]
    assert "wind_shear" in explanation["attribution_weights"]
    assert explanation["attribution_weights"]["sst"] > 0
    assert len(explanation["key_factors"]) >= 4

