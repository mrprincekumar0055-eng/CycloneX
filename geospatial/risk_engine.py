"""
CycloneX Quantitative Risk Engine
Calculates Geographic Disaster Risk based on the UNDRR Framework:
Risk Score = f(Hazard, Exposure, Vulnerability, Uncertainty)

*FORMULA & WEIGHTING SPECIFICATION:*
1. Hazard Score (H):
   H = 0.45 * (wind_kts / 115) + 0.35 * (pressure_deficit / 75) + 0.20 * surge_proxy
2. Exposure Score (E):
   E = [0.65 * (pop / 1,500,000) + 0.35 * (facilities / 50)] * max(0.35, 1 - distance_km / 350)
3. Vulnerability Score (V):
   V = 0.50 * max(0.2, 1 - elevation_m / 20) + 0.50 * baseline_social_vuln (0.65)
4. Uncertainty Scaling (U):
   U = 1.0 - min(0.30, (lead_time_hours / 72.0) * 0.30)
5. Composite Risk Score (R):
   R = (0.40 * H + 0.35 * E + 0.25 * V) * (0.85 + 0.15 * U)

*SCIENTIFIC ASSUMPTIONS & LIMITATIONS:*
- Multi-criteria heuristic model for early-warning ranking; not a calibrated physical hydrodynamic flood simulation.
- Designed for rapid comparative decision support across coastal administrative blocks.
"""
from typing import Dict, Any
from datetime import datetime, timezone

class RiskEngine:
    @staticmethod
    def calculate_risk(
        wind_speed_kts: float,
        central_pressure_hpa: float,
        distance_to_coast_km: float,
        population_count: int,
        critical_infrastructure_count: int,
        coastal_elevation_m: float = 4.0,
        forecast_lead_time_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calculates deterministic, testable disaster risk metrics.
        """
        # 1. Hazard Score (0.0 to 1.0)
        v_norm = min(1.0, max(0.05, wind_speed_kts / 115.0))
        p_norm = min(1.0, max(0.05, (1010.0 - central_pressure_hpa) / 75.0))
        surge_proxy = min(1.0, (wind_speed_kts / 80.0) / max(1.0, coastal_elevation_m * 0.75))
        hazard_score = round(min(1.0, (0.45 * v_norm) + (0.35 * p_norm) + (0.20 * surge_proxy)), 3)

        # 2. Exposure Score (0.0 to 1.0)
        pop_norm = min(1.0, max(0.05, population_count / 1_500_000.0))
        infra_norm = min(1.0, max(0.05, critical_infrastructure_count / 50.0))
        proximity_factor = max(0.35, 1.0 - (distance_to_coast_km / 350.0))
        exposure_score = round(min(1.0, ((0.65 * pop_norm) + (0.35 * infra_norm)) * proximity_factor), 3)

        # 3. Vulnerability Score (0.0 to 1.0)
        elevation_vuln = max(0.2, 1.0 - (coastal_elevation_m / 20.0))
        base_social_vulnerability = 0.65
        vulnerability_score = round(min(1.0, (0.50 * elevation_vuln) + (0.50 * base_social_vulnerability)), 3)

        # 4. Uncertainty Score (0.0 to 1.0 - higher lead time increases uncertainty)
        uncertainty_score = round(min(1.0, max(0.0, forecast_lead_time_hours / 72.0)), 3)
        uncertainty_discount = 1.0 - (0.30 * uncertainty_score)

        # 5. Composite Risk Score
        raw_risk = (0.40 * hazard_score) + (0.35 * exposure_score) + (0.25 * vulnerability_score)
        risk_score = round(min(1.0, max(0.05, raw_risk * (0.85 + 0.15 * uncertainty_discount))), 3)

        # Categorization into discrete operational tiers
        if risk_score >= 0.70:
            risk_category = "Extreme Risk"
            color = "#ef4444"
            alert_tier = "Evacuation Order"
        elif risk_score >= 0.48:
            risk_category = "High Risk"
            color = "#f97316"
            alert_tier = "Cyclone Warning"
        elif risk_score >= 0.28:
            risk_category = "Moderate Risk"
            color = "#eab308"
            alert_tier = "Cyclone Alert / Watch"
        else:
            risk_category = "Low Risk"
            color = "#22c55e"
            alert_tier = "Advisory"

        return {
            "risk_score": risk_score,
            "composite_risk_score": risk_score,
            "risk_category": risk_category,
            "risk_level": risk_category,
            "hazard_score": hazard_score,
            "exposure_score": exposure_score,
            "vulnerability_score": vulnerability_score,
            "uncertainty_score": uncertainty_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "color": color,
            "recommended_alert": alert_tier,
            "disclaimer": "AI/ML methodology based on UNDRR disaster risk paradigm; decision support only.",
            "formula_metadata": {
                "methodology": "Multi-Criteria UNDRR Hazard-Exposure-Vulnerability Synthesis",
                "weights": {"hazard": 0.40, "exposure": 0.35, "vulnerability": 0.25},
                "scientific_status": "Decision-support index; not a validated hydrodynamic numerical surge model."
            },
            "parameters": {
                "wind_speed_kts": wind_speed_kts,
                "central_pressure_hpa": central_pressure_hpa,
                "distance_to_coast_km": distance_to_coast_km,
                "population_count": population_count,
                "critical_infrastructure_count": critical_infrastructure_count,
                "coastal_elevation_m": coastal_elevation_m,
                "forecast_lead_time_hours": forecast_lead_time_hours
            }
        }
