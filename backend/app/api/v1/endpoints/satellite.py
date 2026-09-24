from typing import Optional
from fastapi import APIRouter, Query
from data.adapters.nasa_gibs import NASAGIBSAdapter

router = APIRouter()

@router.get("/layers")
def get_satellite_layers():
    return {
        "status": "online",
        "provider": "NASA GIBS / MODIS / VIIRS",
        "layers": NASAGIBSAdapter.get_available_layers()
    }

@router.get("/tile-url")
def get_tile_url_template(
    layer_id: str = Query("MODIS_Terra_CorrectedReflectance_TrueColor"),
    date_str: Optional[str] = None
):
    tile_url = NASAGIBSAdapter.get_layer_tile_url(layer_id=layer_id, date_str=date_str)
    return {
        "layer_id": layer_id,
        "date": date_str,
        "tile_url_template": tile_url,
        "attribution": "NASA Earth Science Data / GIBS"
    }

