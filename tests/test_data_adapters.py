import pytest
import asyncio
from data.adapters.open_meteo import OpenMeteoAdapter
from data.adapters.osm_overpass import OSMOverpassAdapter
from data.adapters.ibtracs import IBTrACSAdapter
from data.adapters.worldpop import WorldPopAdapter
from data.adapters.osrm import OSRMRoutingAdapter

def test_open_meteo_validation():
    adapter = OpenMeteoAdapter()
    # Valid payload
    assert adapter.validate({
        "current": {"wind_speed_10m": 45.0, "surface_pressure": 985.0}
    }) is True
    # Invalid wind (negative)
    assert adapter.validate({
        "current": {"wind_speed_10m": -5.0, "surface_pressure": 985.0}
    }) is False
    # Missing current
    assert adapter.validate({}) is False

@pytest.mark.anyio
async def test_open_meteo_fallback_on_invalid_endpoint():
    adapter = OpenMeteoAdapter()
    # Invalid lat/lon should trigger resilient fallback without crashing
    res = await adapter.fetch(lat=999.0, lon=999.0)
    assert res["data_status"] in ["LIVE", "DEMO"]
    assert "surface_wind_10m_kts" in res["data"]
    assert res["source"] == "Open-Meteo NWP API"

def test_osm_overpass_validation():
    adapter = OSMOverpassAdapter()
    # Valid facilities list
    assert adapter.validate([{"lat": 23.2, "lon": 68.8, "name": "Shelter A"}]) is True
    # Invalid coordinates
    assert adapter.validate([{"lat": 999.0, "lon": 68.8}]) is False
    # Missing fields
    assert adapter.validate([{"name": "No coords"}]) is False

def test_ibtracs_analog_search():
    analogs = IBTrACSAdapter.find_analogous_cyclones(
        current_lat=21.65,
        current_lon=66.85,
        current_wind_kts=85.0,
        top_k=2
    )
    assert len(analogs) == 2
    assert "similarity_score_pct" in analogs[0]
    assert 0.0 <= analogs[0]["similarity_score_pct"] <= 100.0
    assert "provenance" in analogs[0]
    assert analogs[0]["provenance"]["scientific_role"].startswith("Comparative Historical Analog")

@pytest.mark.anyio
async def test_worldpop_demographic_fetch():
    adapter = WorldPopAdapter()
    res = await adapter.fetch(district="Kutch", radius_km=50.0)
    assert res["data_status"] == "DEMO"
    assert res["data"]["estimated_population"] > 0
    assert res["data"]["vulnerable_population"] > 0

@pytest.mark.anyio
async def test_osrm_routing_fallback():
    adapter = OSRMRoutingAdapter()
    res = await adapter.fetch(
        origin_lat=23.2380, origin_lon=68.6180,
        dest_lat=23.2612, dest_lon=68.8320
    )
    assert res["data_status"] in ["LIVE", "DEMO"]
    assert res["data"]["distance_km"] > 0.0
    assert "disclaimer" in res["data"]

