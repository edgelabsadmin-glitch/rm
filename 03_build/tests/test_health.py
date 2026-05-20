"""SPEC-001 — /health endpoint smoke test."""

from fastapi.testclient import TestClient

from api.main import create_app


def test_health_endpoint_returns_200():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
