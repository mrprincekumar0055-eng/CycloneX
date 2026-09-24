"""
Track Prediction Engine
Predicts future cyclone eye locations (latitude, longitude) at +6h, +12h, +24h, +48h, +72h.
Generates dynamic uncertainty radii representing the cone of uncertainty.
"""
from typing import List, Dict, Any
import math

class TrackPredictor:
    def __init__(self):
        self.horizons = [6, 12, 24, 48, 72]
        # Empirical historical average position error (km) for official basins
        self.base_uncertainty_km = {
            6: 35.0,
            12: 55.0,
            24: 92.0,
            48: 155.0,
            72: 240.0
        }

    def predict_track(
        self,
        current_lat: float,
        current_lon: float,
        heading_deg: float,
        speed_kmh: float,
        recurvature_factor: float = 0.05
    ) -> List[Dict[str, Any]]:
        """
        Projects storm trajectory using steering flow vector and beta-drift recurvature.
        """
        track_points = []
        lat = current_lat
        lon = current_lon
        heading = heading_deg

        prev_h = 0
        for h in self.horizons:
            dt = h - prev_h
            prev_h = h
            
            # Coriolis / Beta-drift induces slight rightward recurvature in Northern Hemisphere
            heading = (heading + (recurvature_factor * dt)) % 360.0
            
            # Distance traveled in km
            dist_km = speed_kmh * dt
            
            # Spherical coordinate projection
            rad = math.radians(heading)
            # 1 deg lat ~ 111.0 km
            d_lat = (dist_km * math.cos(rad)) / 111.0
            # 1 deg lon ~ 111.0 * cos(lat)
            cos_lat = math.cos(math.radians(lat))
            d_lon = (dist_km * math.sin(rad)) / (111.0 * max(0.2, cos_lat))
            
            lat += d_lat
            lon += d_lon
            
            uncertainty_radius = self.base_uncertainty_km.get(h, 250.0)
            
            track_points.append({
                "forecast_hour": h,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "uncertainty_radius_km": round(uncertainty_radius, 1),
                "heading_deg": round(heading, 1),
                "speed_kmh": round(speed_kmh, 1)
            })

        return track_points

