import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from app.main import app, settings


headers = {"X-Internal-Token": settings.app_internal_token, "X-Workspace-ID": "demo-workspace"}

with TestClient(app) as client:
    deadline = time.time() + 45
    documents = []
    while time.time() < deadline:
        response = client.get("/api/documents", headers=headers)
        response.raise_for_status()
        documents = response.json()
        if documents and all(item["status"] in {"indexed", "failed"} for item in documents):
            break
        time.sleep(0.5)

    indexed = [item for item in documents if item["status"] == "indexed"]
    if len(indexed) < 5:
        raise SystemExit(f"Expected at least 5 indexed samples, received: {json.dumps(documents, indent=2)}")

    response = client.post("/api/chat", headers=headers, json={"messages": [{"role": "user", "content": "How much did solar generation increase in 2025?"}]})
    response.raise_for_status()
    answer = response.json()
    if not answer["citations"] or answer["citations"][0]["page_number"] < 1:
        raise SystemExit(f"Expected a page citation, received: {json.dumps(answer, indent=2)}")

    image_response = client.get(answer["citations"][0]["image_url"])
    image_response.raise_for_status()
    if image_response.headers.get("content-type") != "image/jpeg":
        raise SystemExit("Citation did not resolve to a page image")

    print(json.dumps({"indexed_documents": len(indexed), "answer": answer["content"], "citation": answer["citations"][0]}, indent=2))
