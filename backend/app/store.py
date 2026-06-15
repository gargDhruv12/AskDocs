import json
import threading
from pathlib import Path
from .models import DocumentRecord


class DocumentStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._documents: dict[str, DocumentRecord] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        with self._lock:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._documents = {item["id"]: DocumentRecord.model_validate(item) for item in raw}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps([doc.model_dump() for doc in self._documents.values()], indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def put(self, document: DocumentRecord) -> None:
        with self._lock:
            self._documents[document.id] = document
            self.save()

    def get(self, document_id: str, workspace_id: str) -> DocumentRecord | None:
        document = self._documents.get(document_id)
        return document if document and document.workspace_id == workspace_id else None

    def list(self, workspace_id: str) -> list[DocumentRecord]:
        return sorted((doc for doc in self._documents.values() if doc.workspace_id == workspace_id), key=lambda doc: doc.created_at, reverse=True)

    def delete(self, document_id: str, workspace_id: str) -> DocumentRecord | None:
        with self._lock:
            document = self._documents.get(document_id)
            if not document or document.workspace_id != workspace_id:
                return None
            removed = self._documents.pop(document_id)
            self.save()
            return removed
