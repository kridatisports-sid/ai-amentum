"""
tests/test_api.py
Integration tests for FastAPI routes using TestClient.
Firebase and external services are mocked.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Mock Firebase before importing app ───────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_firebase(monkeypatch):
    monkeypatch.setattr("utils.firebase.save_doc",   AsyncMock())
    monkeypatch.setattr("utils.firebase.update_doc", AsyncMock())
    monkeypatch.setattr("utils.firebase.get_doc",    AsyncMock(return_value={
        "video_id":      "test-id",
        "user_id":       "user-123",
        "status":        "complete",
        "overall_score": 74.5,
        "grade":         "Advanced",
        "created_at":    "2025-01-01T00:00:00+00:00",
        "tier":          "free",
        "sections":      [],
        "issues":        [],
        "recommendations": [],
        "key_angles":    {},
        "ai_narrative":  "Great throw!",
        "release_angle": 33.0,
        "duration_sec":  4.5,
    }))
    monkeypatch.setattr("utils.firebase.query_collection", AsyncMock(return_value=[]))
    monkeypatch.setattr("utils.firebase.upload_to_storage", MagicMock(return_value="https://example.com/file"))
    monkeypatch.setattr("utils.firebase._init", MagicMock())


@pytest.fixture(autouse=True)
def mock_auth(monkeypatch):
    monkeypatch.setattr(
        "utils.auth.get_current_user",
        AsyncMock(return_value={"uid": "user-123", "email": "test@test.com"}),
    )


@pytest.fixture
def client():
    from main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_get_analysis_status(client):
    r = client.get("/api/analyze/test-id",
                   headers={"Authorization": "Bearer mock-token"})
    assert r.status_code == 200
    assert r.json()["status"] == "complete"


def test_get_report(client):
    r = client.get("/api/report/test-id",
                   headers={"Authorization": "Bearer mock-token"})
    assert r.status_code == 200
    data = r.json()
    assert data["overall_score"] == 74.5
    assert data["grade"] == "Advanced"


def test_get_history(client):
    r = client.get("/api/report/user/history",
                   headers={"Authorization": "Bearer mock-token"})
    assert r.status_code == 200
    assert "history" in r.json()


def test_upload_wrong_type(client):
    r = client.post(
        "/api/upload/",
        headers={"Authorization": "Bearer mock-token"},
        files={"file": ("test.txt", b"not a video", "text/plain")},
    )
    assert r.status_code == 415
