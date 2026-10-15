import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total" in stats
    assert "completed" in stats

def test_create_and_get_lead():
    res = client.post("/api/leads", json={"input_raw": "https://www.houstonroofingonline.com"})
    assert res.status_code == 200
    lead = res.json()
    assert lead["input_raw"] == "https://www.houstonroofingonline.com"
    lead_id = lead["id"]
    
    # Fetch lead
    res_get = client.get(f"/api/leads/{lead_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == lead_id

def test_export_endpoints():
    res_csv = client.get("/api/leads/export/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    
    res_json = client.get("/api/leads/export/json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
