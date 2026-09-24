from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_location_specific_intelligence_endpoint():
    # Query location intelligence for Jakhau Fishery Port coordinates
    res = client.get("/api/v1/cyclones/demo-biparjoy-2023/location-intelligence?lat=23.2380&lon=68.6180")
    assert res.status_code == 200
    data = res.json()
    
    assert "location" in data
    assert data["location"]["lat"] == 23.238
    assert data["cyclone_distance_km"] > 0
    assert "bearing_deg" in data
    assert "risk" in data
    assert "nearest_shelter" in data
    assert data["nearest_shelter"]["name"] is not None
    assert "nearest_hospital" in data
    assert "evacuation_corridor" in data
    assert len(data["recommended_actions"]) > 0
    assert "disclaimer" in data

def test_location_near_cyclone_center():
    # Cyclone Biparjoy eye is around 21.65°N, 66.85°E
    res = client.get("/api/v1/cyclones/demo-biparjoy-2023/location-intelligence?lat=21.70&lon=66.90")
    assert res.status_code == 200
    data = res.json()
    
    # Distance to eye should be < 25 km
    assert data["cyclone_distance_km"] < 25.0
    # Near the eye, wind estimation should be elevated
    assert data["local_estimated_wind_kts"] > 10.0
    # Risk category should be elevated
    assert data["risk"]["risk_category"] in ["High Risk", "Extreme Risk", "Moderate Risk"]

def test_location_moderate_distance_coastal():
    # Saurashtra coastal town (Porbandar ~21.64°N, 69.62°E)
    res = client.get("/api/v1/cyclones/demo-biparjoy-2023/location-intelligence?lat=21.64&lon=69.62")
    assert res.status_code == 200
    data = res.json()
    
    # Distance should be roughly 250 - 350 km
    assert 200.0 < data["cyclone_distance_km"] < 400.0
    # Bearing should be eastward (~80-100°)
    assert 70.0 <= data["bearing_deg"] <= 110.0
    assert "nearest_shelter" in data
    assert data["nearest_shelter"]["distance_km"] > 0

def test_location_distant_inland():
    # Distant inland city (New Delhi: 28.61°N, 77.20°E)
    res = client.get("/api/v1/cyclones/demo-biparjoy-2023/location-intelligence?lat=28.61&lon=77.20")
    assert res.status_code == 200
    data = res.json()
    
    # Distance should be > 1000 km
    assert data["cyclone_distance_km"] > 1000.0
    # Wind should be decaying to background limit (20 kts)
    assert data["local_estimated_wind_kts"] == 20.0
    # Distance to eye reflects distant inland location
    assert data["bearing_deg"] >= 0.0

def test_location_arbitrary_coordinates_variation():
    # Prove that changing (lat, lon) actually changes all dynamic parameters
    coord_A = (22.82, 69.34) # Mandvi, Kutch
    coord_B = (20.90, 70.37) # Veraval / Somnath
    
    res_A = client.get(f"/api/v1/cyclones/demo-biparjoy-2023/location-intelligence?lat={coord_A[0]}&lon={coord_A[1]}").json()
    res_B = client.get(f"/api/v1/cyclones/demo-biparjoy-2023/location-intelligence?lat={coord_B[0]}&lon={coord_B[1]}").json()
    
    # Distance must differ
    assert res_A["cyclone_distance_km"] != res_B["cyclone_distance_km"]
    # Bearing must differ
    assert res_A["bearing_deg"] != res_B["bearing_deg"]
    # Local wind proxy must differ
    assert res_A["local_estimated_wind_kts"] != res_B["local_estimated_wind_kts"]
    # Risk score must differ
    assert res_A["risk"]["composite_risk_score"] != res_B["risk"]["composite_risk_score"]
    # Evacuation corridor distance and duration must differ
    assert res_A["evacuation_corridor"]["distance_km"] != res_B["evacuation_corridor"]["distance_km"]
