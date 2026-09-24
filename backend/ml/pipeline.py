"""
Unified CycloneX AI/ML Pipeline
Coordinates: Detection -> Classification -> Intensity Prediction -> Track Prediction -> Explainability
"""
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from ml.models.detector import CycloneDetector
from ml.models.classifier import CycloneClassifier
from ml.models.intensity import IntensityPredictor
from ml.models.track import TrackPredictor
from ml.explainability import CycloneExplainer

class CycloneMLPipeline:
    def __init__(self):
        self.detector = CycloneDetector()
        self.classifier = CycloneClassifier()
        self.intensity_predictor = IntensityPredictor()
        self.track_predictor = TrackPredictor()
        self.explainer = CycloneExplainer()
        self.model_version = "v1.2-ensemble-fusion"

    def run_full_inference(
        self,
        cyclone_id: str,
        current_lat: float,
        current_lon: float,
        current_wind_kts: float,
        current_pressure_hpa: float,
        current_heading_deg: float,
        current_speed_kmh: float,
        sst_c: float = 29.5,
        wind_shear_kts: float = 11.0,
        cloud_top_temp_c: float = -74.0,
        population_exposed: int = 1_250_000,
        base_timestamp: datetime = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end multi-modal inference pipeline.
        """
        if base_timestamp is None:
            base_timestamp = datetime.now(timezone.utc)

        # 1. Detection
        pressure_deficit = max(0.0, 1010.0 - current_pressure_hpa)
        detection_features = {
            "central_pressure_deficit": pressure_deficit,
            "max_wind_kts": current_wind_kts,
            "sst_c": sst_c,
            "wind_shear_kts": wind_shear_kts,
            "relative_humidity_pct": 84.0,
            "cloud_top_temp_c": cloud_top_temp_c
        }
        is_detected, detection_prob, det_metrics = self.detector.detect(detection_features)

        # 2. Classification
        current_class = self.classifier.classify_imd(current_wind_kts)

        # 3. Track Prediction
        track_points = self.track_predictor.predict_track(
            current_lat=current_lat,
            current_lon=current_lon,
            heading_deg=current_heading_deg,
            speed_kmh=current_speed_kmh
        )

        # 4. Intensity Prediction
        intensity_points = self.intensity_predictor.forecast_intensity(
            current_wind_kts=current_wind_kts,
            current_pressure_hpa=current_pressure_hpa,
            sst_c=sst_c,
            wind_shear_kts=wind_shear_kts
        )

        # Combine Track and Intensity at each horizon
        forecast_points = []
        for tp, ip in zip(track_points, intensity_points):
            h = tp["forecast_hour"]
            valid_time = base_timestamp + timedelta(hours=h)
            cat = self.classifier.classify_imd(ip["predicted_wind_speed_kts"])
            
            forecast_points.append({
                "forecast_hour": h,
                "valid_time": valid_time.isoformat(),
                "lat": tp["lat"],
                "lon": tp["lon"],
                "predicted_wind_speed_kts": ip["predicted_wind_speed_kts"],
                "predicted_wind_speed_kmh": ip["predicted_wind_speed_kmh"],
                "predicted_pressure_hpa": ip["predicted_pressure_hpa"],
                "category": cat["imd_label"],
                "imd_code": cat["imd_code"],
                "color": cat["color"],
                "uncertainty_radius_km": tp["uncertainty_radius_km"],
                "confidence_score": ip["confidence_score"]
            })

        # 5. Explainability
        explanation = self.explainer.explain_prediction(
            sst_c=sst_c,
            wind_shear_kts=wind_shear_kts,
            central_pressure_deficit=pressure_deficit,
            wind_trend="Intensifying",
            proximity_to_coast_km=145.0,
            population_exposed=population_exposed
        )

        return {
            "cyclone_id": cyclone_id,
            "model_version": self.model_version,
            "inference_timestamp": base_timestamp.isoformat(),
            "detection": {
                "detected": is_detected,
                "probability": detection_prob,
                "status": "Tropical Cyclone Identified" if is_detected else "Disturbance",
                "metrics": det_metrics
            },
            "classification": current_class,
            "forecast_points": forecast_points,
            "explanation": explanation
        }

ml_pipeline = CycloneMLPipeline()

