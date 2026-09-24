"""
Geospatial Uncertainty Cone & Wind Radii Generator
Generates track uncertainty envelopes calibrated to historical North Indian Ocean position errors.
"""
from typing import List, Dict, Any
import math
from shapely.geometry import Point, Polygon, LineString, mapping
from shapely.ops import unary_union

class ConeGenerator:
    # Official historical average forecast position error radii (km) for North Indian Ocean
    # Source: IMD Official Cyclone Forecasters Guide & RSMC New Delhi 5-year averages
    EMPIRICAL_ERROR_RADII_KM = {
        6: 35.0,
        12: 55.0,
        24: 92.0,
        48: 155.0,
        72: 240.0
    }

    @classmethod
    def generate_uncertainty_cone(cls, forecast_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Builds an empirical position-error uncertainty envelope along the forecast track.
        *SCIENTIFIC NOTICE:*
        This envelope represents the 68% (1-sigma) circle of error around the forecast center.
        It does not delineate the boundary of storm effects (wind/surge extend further).
        """
        if not forecast_points:
            return {"type": "FeatureCollection", "features": []}

        circle_polygons = []
        for pt in forecast_points:
            lat = pt["lat"]
            lon = pt["lon"]
            hour = pt.get("forecast_hour", 24)
            radius_km = pt.get("uncertainty_radius_km", cls.EMPIRICAL_ERROR_RADII_KM.get(hour, 90.0))
            
            deg_lat = radius_km / 111.0
            deg_lon = radius_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
            deg_radius = (deg_lat + deg_lon) / 2.0
            
            p = Point(lon, lat).buffer(deg_radius, quad_segs=16)
            circle_polygons.append(p)

        cone_poly = unary_union(circle_polygons).convex_hull
        
        return {
            "type": "Feature",
            "properties": {
                "name": "Forecast Track Uncertainty Envelope (68% Historical Empirical Confidence)",
                "methodology": "Empirical Error-Based Uncertainty Approximation (IMD/RSMC 5-Year NI Track Errors)",
                "confidence_level": 0.68,
                "scientific_limitation": "Covers predicted storm center location only; severe winds and surge extend significantly outside the envelope."
            },
            "geometry": mapping(cone_poly)
        }

    @staticmethod
    def generate_wind_swath_polygons(
        current_lat: float,
        current_lon: float,
        wind_speed_kts: float
    ) -> List[Dict[str, Any]]:
        """
        Generates 34kt (gale), 50kt (storm), and 64kt (hurricane/severe) wind swaths.
        """
        r64_km = max(0.0, (wind_speed_kts - 64.0) * 2.2 + 45.0) if wind_speed_kts >= 64 else 0.0
        r50_km = max(0.0, (wind_speed_kts - 50.0) * 3.0 + 80.0) if wind_speed_kts >= 50 else 0.0
        r34_km = max(50.0, wind_speed_kts * 2.5 + 70.0)

        layers = []
        swaths = [
            ("64kt_hurricane", r64_km, "Destructive Hurricane Winds (>= 64 kts)", "#ef4444", 0.35),
            ("50kt_storm", r50_km, "Severe Storm Winds (>= 50 kts)", "#f97316", 0.25),
            ("34kt_gale", r34_km, "Gale-Force Winds (>= 34 kts)", "#eab308", 0.18),
        ]

        for code, radius_km, desc, color, fill_opacity in swaths:
            if radius_km <= 0:
                continue
            deg_r = radius_km / 111.0
            poly = Point(current_lon, current_lat).buffer(deg_r, quad_segs=24)
            layers.append({
                "type": "Feature",
                "properties": {
                    "layer_id": code,
                    "description": desc,
                    "radius_km": radius_km,
                    "color": color,
                    "fillOpacity": fill_opacity
                },
                "geometry": mapping(poly)
            })

        return layers
