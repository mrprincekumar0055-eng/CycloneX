"""
NASA GIBS / MODIS Satellite Imagery Adapter
Constructs WMTS tile templates and queries bounding box tiles.
Implements BaseAdapter with validation and provenance tracking.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import time
from data.adapters.base import BaseAdapter

class NASAGIBSAdapter(BaseAdapter):
    BASE_WMTS = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"
    
    LAYERS = {
        "MODIS_Terra_CorrectedReflectance_TrueColor": {
            "title": "MODIS Terra True Color (Corrected Reflectance)",
            "format": "jpg",
            "matrix_set": "250m",
            "default_opacity": 0.85
        },
        "MODIS_Terra_SurfaceReflectance_Bands721": {
            "title": "MODIS False Color (Bands 7-2-1 Storm Structure)",
            "format": "jpg",
            "matrix_set": "250m",
            "default_opacity": 0.75
        },
        "VIIRS_SNPP_CorrectedReflectance_TrueColor": {
            "title": "VIIRS SNPP True Color",
            "format": "jpg",
            "matrix_set": "250m",
            "default_opacity": 0.85
        }
    }

    def __init__(self):
        super().__init__(
            source_name="NASA GIBS (Global Imagery Browse Services)",
            source_url="https://gibs.earthdata.nasa.gov"
        )

    def validate(self, raw_data: Any) -> bool:
        if not isinstance(raw_data, dict):
            return False
        return "layer_id" in raw_data and "tile_url_template" in raw_data

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        return raw_data

    async def fetch(
        self,
        layer_id: str = "MODIS_Terra_CorrectedReflectance_TrueColor",
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        start = time.time()
        if layer_id not in self.LAYERS:
            layer_id = "MODIS_Terra_CorrectedReflectance_TrueColor"
            
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
        cfg = self.LAYERS[layer_id]
        ext = cfg["format"]
        matrix = cfg["matrix_set"]
        
        url_template = f"{self.BASE_WMTS}/{layer_id}/default/{date_str}/{matrix}/{{z}}/{{y}}/{{x}}.{ext}"
        
        payload = {
            "layer_id": layer_id,
            "title": cfg["title"],
            "date": date_str,
            "tile_url_template": url_template,
            "attribution": "NASA Earth Science Data & Information System (ESDIS) / GIBS",
            "supported_matrix_set": matrix
        }

        return self.build_provenance_envelope(
            payload=payload,
            observation_time=f"{date_str}T00:00:00Z",
            data_status="LIVE",
            start_time_seconds=start
        )

    @classmethod
    def get_layer_tile_url(cls, layer_id: str, date_str: str = None) -> str:
        if layer_id not in cls.LAYERS:
            layer_id = "MODIS_Terra_CorrectedReflectance_TrueColor"
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cfg = cls.LAYERS[layer_id]
        return f"{cls.BASE_WMTS}/{layer_id}/default/{date_str}/{cfg['matrix_set']}/{{z}}/{{y}}/{{x}}.{cfg['format']}"

    @classmethod
    def get_available_layers(cls) -> List[Dict[str, Any]]:
        return [
            {
                "layer_id": k,
                "title": v["title"],
                "format": v["format"],
                "default_opacity": v["default_opacity"],
                "attribution": "NASA ESDIS GIBS"
            }
            for k, v in cls.LAYERS.items()
        ]

nasa_gibs_adapter = NASAGIBSAdapter()
