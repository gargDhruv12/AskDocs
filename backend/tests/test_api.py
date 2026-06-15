from fastapi.testclient import TestClient
from app.main import app, settings


HEADERS = {"X-Internal-Token": settings.app_internal_token, "X-Workspace-ID": "demo-workspace"}


def test_protected_endpoint_rejects_missing_internal_token():
    with TestClient(app) as client:
        response = client.get("/api/documents", headers={"X-Workspace-ID": "demo-workspace"})
    assert response.status_code == 401


def test_chat_refuses_when_no_relevant_evidence_exists():
    empty_workspace_headers = {**HEADERS, "X-Workspace-ID": "empty-test-workspace"}
    with TestClient(app) as client:
        response = client.post("/api/chat", headers=empty_workspace_headers, json={"messages": [{"role": "user", "content": "What is the launch code for a submarine on Mars?"}]})
    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    assert "couldn't find enough relevant evidence" in body["content"]


def test_api_adds_security_headers():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
