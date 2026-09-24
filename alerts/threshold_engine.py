"""
CycloneX Automated Risk & Threshold Evaluation Engine
Evaluates cyclone predictions against multi-factor operational criteria:
- Predicted Intensity (Peak sustained winds, barometric pressure deficit)
- Track Proximity & Landfall ETA (distance to coastline/settlements)
- Forecast Uncertainty (cone dispersion at target horizon)
- Demographic & Critical Infrastructure Exposure
Determines operational alert level: Advisory -> Watch -> Warning -> Emergency
"""
from typing import Dict, Any, Tuple, List, Optional
import math

class AlertThresholdEngine:
    # IMD / WMO Intensity Benchmarks (kts)
    WIND_DEPRESSION_KTS = 28.0       # Advisory threshold
    WIND_CYCLONIC_STORM_KTS = 34.0   # Watch threshold (CS)
    WIND_SEVERE_CS_KTS = 48.0        # Warning threshold (SCS / VSCS)
    WIND_EXTREME_CS_KTS = 64.0       # Emergency threshold (ESCS / Super Cyclone)

    # Lead Time Landfall Thresholds (hours)
    ETA_WATCH_HOURS = 72
    ETA_WARNING_HOURS = 48
    ETA_EMERGENCY_HOURS = 24

    @classmethod
    def calculate_risk_score(
        cls,
        predicted_wind_kts: float,
        central_pressure_hpa: float,
        landfall_eta_hours: float,
        uncertainty_radius_km: float = 60.0,
        exposed_population: int = 500_000,
        has_critical_infrastructure: bool = True
    ) -> float:
        """
        Computes composite normalized risk index [0.0, 1.0]:
        40% Intensity + 30% Proximity/ETA + 15% Uncertainty + 15% Vulnerable Exposure
        """
        # 1. Intensity factor (normalized to 140 kts max)
        wind_factor = min(1.0, max(0.0, predicted_wind_kts / 135.0))
        pressure_deficit = max(0.0, 1010.0 - central_pressure_hpa)
        pressure_factor = min(1.0, pressure_deficit / 70.0)
        intensity_component = 0.65 * wind_factor + 0.35 * pressure_factor

        # 2. Landfall proximity / ETA factor (closer ETA = higher urgency)
        if landfall_eta_hours <= 0:
            eta_factor = 1.0
        elif landfall_eta_hours <= 12:
            eta_factor = 0.95
        elif landfall_eta_hours <= 24:
            eta_factor = 0.85
        elif landfall_eta_hours <= 48:
            eta_factor = 0.70
        elif landfall_eta_hours <= 72:
            eta_factor = 0.50
        else:
            eta_factor = max(0.1, 1.0 - (landfall_eta_hours / 120.0))

        # 3. Forecast confidence / uncertainty factor (higher uncertainty at short range increases risk buffer)
        norm_uncertainty = min(1.0, max(0.1, uncertainty_radius_km / 150.0))

        # 4. Exposure & infrastructure factor
        pop_factor = min(1.0, math.log10(max(10_000, exposed_population)) / 7.0) # 10M = 1.0
        infra_multiplier = 1.15 if has_critical_infrastructure else 1.0
        exposure_component = min(1.0, pop_factor * infra_multiplier)

        # Composite weighted risk score
        risk_score = (
            0.40 * intensity_component +
            0.30 * eta_factor +
            0.15 * norm_uncertainty +
            0.15 * exposure_component
        )
        return round(min(1.0, max(0.0, risk_score)), 3)

    @classmethod
    def evaluate_threshold(
        cls,
        predicted_wind_kts: float,
        central_pressure_hpa: float,
        landfall_eta_hours: float,
        uncertainty_radius_km: float = 60.0,
        exposed_population: int = 500_000,
        has_critical_infrastructure: bool = True
    ) -> Dict[str, Any]:
        """
        Determines whether thresholds are crossed and returns alert level,
        trigger rationale, and recommended action guidelines.
        """
        risk_score = cls.calculate_risk_score(
            predicted_wind_kts=predicted_wind_kts,
            central_pressure_hpa=central_pressure_hpa,
            landfall_eta_hours=landfall_eta_hours,
            uncertainty_radius_km=uncertainty_radius_km,
            exposed_population=exposed_population,
            has_critical_infrastructure=has_critical_infrastructure
        )

        # Emergency: Extreme Risk (Wind >= 64 kt with ETA <= 24h, or Risk >= 0.82)
        if (predicted_wind_kts >= cls.WIND_EXTREME_CS_KTS and landfall_eta_hours <= cls.ETA_EMERGENCY_HOURS) or risk_score >= 0.82:
            level = "Emergency"
            category = "Extremely Severe / Super Cyclonic Threat"
            trigger_reason = (
                f"Catastrophic threat profile: sustained winds {int(predicted_wind_kts)} kt "
                f"({int(predicted_wind_kts * 1.852)} km/h), landfall within {int(landfall_eta_hours)}h, "
                f"composite risk score {risk_score:.2f}."
            )
            actions_priority = "IMMEDIATE MANDATORY EVACUATION & EMERGENCY READINESS"

        # Warning: High Risk (Wind >= 48 kt with ETA <= 48h, or Risk >= 0.65)
        elif (predicted_wind_kts >= cls.WIND_SEVERE_CS_KTS and landfall_eta_hours <= cls.ETA_WARNING_HOURS) or risk_score >= 0.65:
            level = "Warning"
            category = "Severe / Very Severe Cyclonic Storm Warning"
            trigger_reason = (
                f"Severe cyclonic hazard: sustained winds {int(predicted_wind_kts)} kt "
                f"({int(predicted_wind_kts * 1.852)} km/h), landfall within {int(landfall_eta_hours)}h, "
                f"composite risk score {risk_score:.2f}."
            )
            actions_priority = "PRE-EMPTIVE EVACUATION & SHELTER ACTIVATION"

        # Watch: Moderate Risk (Wind >= 34 kt with ETA <= 72h, or Risk >= 0.45)
        elif (predicted_wind_kts >= cls.WIND_CYCLONIC_STORM_KTS and landfall_eta_hours <= cls.ETA_WATCH_HOURS) or risk_score >= 0.45:
            level = "Watch"
            category = "Cyclonic Storm Watch"
            trigger_reason = (
                f"Formative cyclone trajectory: sustained winds {int(predicted_wind_kts)} kt, "
                f"approach window {int(landfall_eta_hours)}h, composite risk score {risk_score:.2f}."
            )
            actions_priority = "LOGISTICS STAGING & COASTAL ADVISORY"

        # Advisory: Low Risk (Wind >= 28 kt or Risk >= 0.30)
        elif predicted_wind_kts >= cls.WIND_DEPRESSION_KTS or risk_score >= 0.30:
            level = "Advisory"
            category = "Deep Depression / Cyclone Formation Advisory"
            trigger_reason = (
                f"Atmospheric disturbance approaching cyclonic threshold: sustained winds {int(predicted_wind_kts)} kt, "
                f"composite risk score {risk_score:.2f}."
            )
            actions_priority = "FISHERMEN RECALL & MARITIME MONITORING"

        else:
            level = "Normal"
            category = "Ambient Meteorological State"
            trigger_reason = f"Observations within ambient parameters (risk score {risk_score:.2f})."
            actions_priority = "ROUTINE MONITORING"

        return {
            "is_alert_triggered": level != "Normal",
            "alert_level": level,
            "risk_score": risk_score,
            "category": category,
            "trigger_reason": trigger_reason,
            "actions_priority": actions_priority,
            "criteria": {
                "predicted_wind_kts": predicted_wind_kts,
                "central_pressure_hpa": central_pressure_hpa,
                "landfall_eta_hours": landfall_eta_hours,
                "uncertainty_radius_km": uncertainty_radius_km,
                "exposed_population": exposed_population
            }
        }

