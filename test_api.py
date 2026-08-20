"""
Minimal smoke tests using FastAPI's TestClient.
Run with:  pytest test_api.py
"""
import os

os.environ["API_KEY"] = "test-key-123"

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_no_key_needed():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_get_data_missing_key():
    r = client.get("/api/data")
    assert r.status_code == 401


def test_get_data_wrong_key():
    r = client.get("/api/data", headers={"x-api-key": "wrong"})
    assert r.status_code == 401


def test_get_data_correct_key():
    r = client.get("/api/data", headers={"x-api-key": "test-key-123"})
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_post_data_correct_key():
    r = client.post("/api/data", headers={"x-api-key": "test-key-123"}, json={})
    assert r.status_code == 200
    assert r.json() == {"message": "POST received"}


def test_post_data_missing_key():
    r = client.post("/api/data", json={})
    assert r.status_code == 401
