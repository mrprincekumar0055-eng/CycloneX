"""
OSRM Routing Adapter for Evacuation Intelligence
Queries road network routing via Open Source Routing Machine (OSRM).
Implements BaseAdapter with geodesic fallback and mandatory disaster decision-support disclaimer.
"""
from typing import Dict, Any, List, Optional
import httpx
import time
import math
import logging
from data.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

class OSRMRoutingAdapter(BaseAdapter):
    OSRM_PUBLIC_API = "http://router.project-osrm.org/route/v1/driving"

    def __init__(self):
        super().__init__(
            source_name="OSRM Road Routing Engine",
            source_url="http://project-osrm.org"
        )

    def validate(self, raw_data: Any) -> bool:
        if not isinstance(raw_data, dict):
            return False
        return "routes" in raw_data or "distance_km" in raw_data

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "distance_km": round(float(raw_data.get("distance_km", 0.0)), 2),
            "travel_time_minutes": round(float(raw_data.get("travel_time_minutes", 0.0)), 1),
            "route_geojson": raw_data.get("route_geojson", {}),
            "routing_engine": "OSRM / Geodesic Multi-Segment Corridors",
            "disclaimer": "AI-calculated shortest road/geodesic path. Differentiate from State Police or District Magistrate declared official evacuation routes."
        }

    async def fetch(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        timeout_seconds: float = 2.5
    ) -> Dict[str, Any]:
        start = time.time()
        url = f"{self.OSRM_PUBLIC_API}/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
        
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    routes = data.get("routes", [])
                    if routes:
                        r0 = routes[0]
                        dist_km = r0.get("distance", 0.0) / 1000.0
                        duration_mins = r0.get("duration", 0.0) / 60.0
                        geo = r0.get("geometry", {})
                        
                        norm = self.normalize({
                            "distance_km": dist_km,
                            "travel_time_minutes": duration_mins,
                            "route_geojson": {
                                "type": "Feature",
                                "geometry": geo,
                                "properties": {"distance_km": dist_km, "duration_mins": duration_mins}
                            }
                        })
                        return self.build_provenance_envelope(
                            payload=norm,
                            data_status="LIVE",
                            start_time_seconds=start
                        )
        except Exception as e:
            logger.warning(f"OSRM live API unreachable ({e}); computing great-circle road route fallback.")

        # Geodesic road corridor fallback
        # Haversine distance
        dlat = math.radians(dest_lat - origin_lat)
        dlon = math.radians(dest_lon - origin_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(origin_lat)) * math.cos(math.radians(dest_lat)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_km = 6371.0 * c
        duration_mins = (dist_km / 35.0) * 60.0

        # Generate smooth polyline
        steps = max(5, int(dist_km / 2.0))
        coords = []
        for i in range(steps + 1):
            t = i / steps
            lat = origin_lat + t * (dest_lat - origin_lat) + math.sin(t * math.pi) * 0.005
            lon = origin_lon + t * (dest_lon - origin_lon) + math.cos(t * math.pi) * 0.004
            coords.append([round(lon, 5), round(lat, 5)])

        norm = self.normalize({
            "distance_km": dist_km,
            "travel_time_minutes": duration_mins,
            "route_geojson": {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {"distance_km": round(dist_km, 2), "duration_mins": round(duration_mins, 1)}
            }
        })
        return self.build_provenance_envelope(
            payload=norm,
            data_status="DEMO",
            start_time_seconds=start
        )

osrm_adapter = OSRMRoutingAdapter()

