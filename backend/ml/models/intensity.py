"""
Intensity Forecast Engine
Predicts future maximum sustained wind speed and central minimum pressure
at horizons: +6h, +12h, +24h, +48h, +72h.
Considers current wind, SST, wind shear, and moisture flux.
"""
from typing import List, Dict, Any
import numpy as np

class IntensityPredictor:
    def __init__(self):
        self.horizons = [6, 12, 24, 48, 72]

    def forecast_intensity(
        self,
        current_wind_kts: float,
        current_pressure_hpa: float,
        sst_c: float = 29.5,
        wind_shear_kts: float = 10.0,
        is_approaching_land: bool = False,
        landfall_hours_away: float = 36.0
    ) -> List[Dict[str, Any]]:
        """
        Calculates intensity progression following thermodynamic potential and friction upon landfall.
        """
        # Maximum Potential Intensity (MPI) proxy
        # When SST > 28°C and shear < 15kt, intensification rate is positive until land interaction
        sst_factor = max(0.0, (sst_c - 26.5) * 1.8)
        shear_penalty = max(0.0, (wind_shear_kts - 12.0) * 1.2)
        net_drift = (sst_factor - shear_penalty)

        forecasts = []
        w = current_wind_kts
        p = current_pressure_hpa

        for h in self.horizons:
            # Check if land interaction has begun
            if is_approaching_land and h >= landfall_hours_away:
                # Land dissipation: rapid decay
                hours_past_landfall = h - landfall_hours_away
                decay_rate = 0.85 ** (hours_past_landfall / 12.0)
                w = max(20.0, w * decay_rate)
                p = min(1008.0, p + (1008.0 - p) * (1 - decay_rate))
            else:
                # Sea intensification / steady state
                rate_per_hour = (net_drift / 24.0)
                w_change = rate_per_hour * (6 if h == 6 else (h - (h//2)))
                w = float(np.clip(w + w_change, 20.0, 155.0))
                # Atmospheric hydrostatic pressure coupling (Atkinson-Holliday relationship)
                p = round(1010.0 - ((w / 0.95) ** 1.35) * 0.12, 1)

            # Error / Uncertainty bounds widen with forecast horizon
            mae_wind = 4.5 + (h / 72.0) * 12.0
            
            forecasts.append({
                "forecast_hour": h,
                "predicted_wind_speed_kts": round(w, 1),
                "predicted_wind_speed_kmh": round(w * 1.852, 1),
                "predicted_pressure_hpa": round(p, 1),
                "mae_wind_kts": round(mae_wind, 1),
                "confidence_score": round(max(0.60, 0.95 - (h / 72.0) * 0.30), 2)
            })

        return forecasts

