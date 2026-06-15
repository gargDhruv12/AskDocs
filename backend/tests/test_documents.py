from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app, settings, store
from app.models import DocumentRecord, PageRecord
from app.rag import retrieve


def headers(workspace: str) -> dict[str, str]:
    return {"X-Internal-Token": settings.app_internal_token, "X-Workspace-ID": workspace}


def record(workspace: str, status: str = "indexed", origin: str = "upload") -> DocumentRecord:
    identifier = uuid4().hex
    original = settings.upload_dir / workspace / f"{identifier}.pdf"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(b"test document")
    return DocumentRecord(
        id=identifier,
        workspace_id=workspace,
        name="test-document.pdf",
        storage_path=str(original),
        mime_type="application/pdf",
        status=status,
        origin=origin,
    )


def test_page_manifest_is_ordered_signed_and_workspace_scoped(tmp_path: Path):
    workspace = f"pages-{uuid4().hex}"
    document = record(workspace)
    document.page_count = 2
    document.pages = [
        PageRecord(page_number=2, text="second", image_path=str(tmp_path / "2.jpg")),
        PageRecord(page_number=1, text="first", image_path=str(tmp_path / "1.jpg")),
    ]
    store.put(document)
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/documents/{document.id}/pages", headers=headers(workspace))
            foreign = client.get(f"/api/documents/{document.id}/pages", headers=headers(f"other-{workspace}"))
        assert response.status_code == 200
        body = response.json()
        assert body["document_id"] == document.id
        assert [page["page_number"] for page in body["pages"]] == [1, 2]
        assert all("expires=" in page["image_url"] and "signature=" in page["image_url"] for page in body["pages"])
        assert foreign.status_code == 404
    finally:
        store.delete(document.id, workspace)


def test_delete_removes_upload_original_pages_metadata_and_retrieval():
    workspace = f"delete-{uuid4().hex}"
    document = record(workspace)
    page_directory = settings.page_dir / workspace / document.id
    page_directory.mkdir(parents=True, exist_ok=True)
    image = page_directory / "page-1.jpg"
    image.write_bytes(b"image")
    document.page_count = 1
    document.pages = [PageRecord(page_number=1, text="unique deletion evidence", image_path=str(image))]
    store.put(document)

    with TestClient(app) as client:
        response = client.delete(f"/api/documents/{document.id}", headers=headers(workspace))

    assert response.status_code == 204
    assert store.get(document.id, workspace) is None
    assert not Path(document.storage_path).exists()
    assert not page_directory.exists()
    assert retrieve(["unique deletion evidence"], store.list(workspace)) == []


def test_delete_rejects_sample_processing_missing_and_foreign_documents():
    workspace = f"guards-{uuid4().hex}"
    sample = record(workspace, origin="sample")
    processing = record(workspace, status="indexing")
    store.put(sample)
    store.put(processing)
    try:
        with TestClient(app) as client:
            sample_response = client.delete(f"/api/documents/{sample.id}", headers=headers(workspace))
            processing_response = client.delete(f"/api/documents/{processing.id}", headers=headers(workspace))
            missing_response = client.delete(f"/api/documents/{uuid4().hex}", headers=headers(workspace))
            foreign_response = client.delete(f"/api/documents/{processing.id}", headers=headers(f"other-{workspace}"))
        assert sample_response.status_code == 403
        assert processing_response.status_code == 409
        assert missing_response.status_code == 404
        assert foreign_response.status_code == 404
    finally:
        Path(sample.storage_path).unlink(missing_ok=True)
        Path(processing.storage_path).unlink(missing_ok=True)
        store.delete(sample.id, workspace)
        store.delete(processing.id, workspace)


def test_delete_rejects_storage_path_outside_workspace(tmp_path: Path):
    workspace = f"containment-{uuid4().hex}"
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"must remain")
    document = DocumentRecord(
        id=uuid4().hex,
        workspace_id=workspace,
        name="outside.pdf",
        storage_path=str(outside),
        mime_type="application/pdf",
        status="indexed",
    )
    store.put(document)
    try:
        with TestClient(app) as client:
            response = client.delete(f"/api/documents/{document.id}", headers=headers(workspace))
        assert response.status_code == 400
        assert outside.exists()
        assert store.get(document.id, workspace) is not None
    finally:
        store.delete(document.id, workspace)
