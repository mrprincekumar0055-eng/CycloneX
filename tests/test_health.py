from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "CycloneX"
    assert "api_docs" in data

def test_health_check():
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["active_cyclones_count"] >= 1
    assert "version" in data

def test_system_readiness():
    response = client.get("/api/v1/system/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["status"] == "ready"
    assert data["database_connected"] is True
    assert data["tables_healthy"] is True
    assert data["table_counts"]["cyclones"] >= 1
    assert data["table_counts"]["alerts"] >= 1
    assert data["table_counts"]["shelters"] >= 1
    assert data["table_counts"]["hospitals"] >= 1
    assert data["map_tile_provider"]["verified"] is True


