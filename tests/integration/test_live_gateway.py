import pytest
from llm_gate.api import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_live_gateway_integration():
    # Hit health endpoint natively
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    
    # Hit parsing endpoint
    resp = client.post("/route", json={"task": "Deploy production", "criticality": "critical"})
    assert resp.status_code == 200
    data = resp.json()
    assert "model" in data
    assert data["tier"] == 0
    assert "critical" in data["reason"]

    # Hit fallback
    resp = client.post("/route", json={"task": "Format JSON", "criticality": "low"})
    assert resp.status_code == 200
