from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import hashlib
import shutil
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from .config import get_settings
from .llm import GroqService
from .models import ChatRequest, ChatResponse, DocumentPage, DocumentPagesResponse, DocumentRecord
from .parser import parse_document
from .rag import evidence_block, retrieve, validated_citations
from .security import SlidingWindowRateLimiter, require_internal_token, safe_display_name, sign_page, validate_upload, verify_page_signature, workspace_id
from .store import DocumentStore

settings = get_settings()
store = DocumentStore(settings.app_data_dir / "documents.json")
llm = GroqService(settings)
executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="document-worker")
rate_limiter = SlidingWindowRateLimiter()


def seed_sample_documents() -> None:
    if not settings.seed_samples or not settings.app_sample_dir.exists():
        return
    for source in sorted(settings.app_sample_dir.glob("*.pdf")):
        identifier = hashlib.sha256(source.read_bytes()).hexdigest()[:32]
        existing = store.get(identifier, "demo-workspace")
        if existing:
            if existing.origin != "sample":
                existing.origin = "sample"
                store.put(existing)
            continue
        target = settings.upload_dir / "demo-workspace" / f"{identifier}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        document = DocumentRecord(id=identifier, workspace_id="demo-workspace", name=source.name, storage_path=str(target), mime_type="application/pdf", origin="sample")
        store.put(document)
        executor.submit(process_document, identifier, "demo-workspace")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_sample_documents()
    yield
    executor.shutdown(wait=False, cancel_futures=False)


app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/api/docs", redoc_url=None, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.app_origins.split(",")], allow_credentials=False, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "X-Workspace-ID"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
    return response


def public_document(document: DocumentRecord) -> dict:
    return document.model_dump(exclude={"workspace_id", "storage_path", "pages"})


def authorize(token: str | None) -> None:
    require_internal_token(token, settings.app_internal_token)


def signed_page_url(document: DocumentRecord, page_number: int) -> str:
    expires, signature = sign_page(document.workspace_id, document.id, page_number, settings.app_signing_secret)
    return f"/api/documents/{document.id}/pages/{page_number}/image?workspace={document.workspace_id}&expires={expires}&signature={signature}"


def contained_path(path: Path, root: Path) -> Path:
    resolved_path = path.resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    if resolved_root not in resolved_path.parents:
        raise HTTPException(status_code=400, detail="Document storage path is invalid")
    return resolved_path


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "groq_configured": bool(settings.groq_api_key), "documents": len(store.list("demo-workspace"))}


@app.get("/api/documents")
def list_documents(x_workspace_id: str | None = Header(default=None), x_internal_token: str | None = Header(default=None)) -> list[dict]:
    authorize(x_internal_token)
    return [public_document(doc) for doc in store.list(workspace_id(x_workspace_id))]


@app.get("/api/documents/{document_id}")
def get_document(document_id: str, x_workspace_id: str | None = Header(default=None), x_internal_token: str | None = Header(default=None)) -> dict:
    authorize(x_internal_token)
    document = store.get(document_id, workspace_id(x_workspace_id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return public_document(document)


@app.get("/api/documents/{document_id}/pages", response_model=DocumentPagesResponse)
def document_pages(document_id: str, x_workspace_id: str | None = Header(default=None), x_internal_token: str | None = Header(default=None)) -> DocumentPagesResponse:
    authorize(x_internal_token)
    workspace = workspace_id(x_workspace_id)
    document = store.get(document_id, workspace)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    pages = [DocumentPage(page_number=page.page_number, image_url=signed_page_url(document, page.page_number)) for page in sorted(document.pages, key=lambda item: item.page_number)]
    return DocumentPagesResponse(document_id=document.id, document_name=document.name, page_count=document.page_count, pages=pages)


@app.post("/api/documents/upload", status_code=202)
async def upload(request: Request, files: list[UploadFile] = File(...), x_workspace_id: str | None = Header(default=None), x_internal_token: str | None = Header(default=None)) -> list[dict]:
    authorize(x_internal_token)
    workspace = workspace_id(x_workspace_id)
    client = request.client.host if request.client else "unknown"
    rate_limiter.check(f"upload:{workspace}:{client}", settings.upload_requests_per_minute)
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Upload up to 10 files at a time")
    created = []
    for file in files:
        data, extension = await validate_upload(file, settings.max_upload_mb * 1024 * 1024)
        identifier = uuid4().hex
        target = settings.upload_dir / workspace / f"{identifier}{extension}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        document = DocumentRecord(id=identifier, workspace_id=workspace, name=safe_display_name(file.filename), storage_path=str(target), mime_type=file.content_type or "application/octet-stream")
        store.put(document)
        executor.submit(process_document, identifier, workspace)
        created.append(public_document(document))
    return created


@app.delete("/api/documents/{document_id}", status_code=204)
def delete_document(document_id: str, x_workspace_id: str | None = Header(default=None), x_internal_token: str | None = Header(default=None)) -> Response:
    authorize(x_internal_token)
    workspace = workspace_id(x_workspace_id)
    document = store.get(document_id, workspace)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.origin == "sample":
        raise HTTPException(status_code=403, detail="Bundled sample documents cannot be removed")
    if document.status not in {"indexed", "failed"}:
        raise HTTPException(status_code=409, detail="Wait for document processing to finish before removing it")

    original = contained_path(Path(document.storage_path), settings.upload_dir / workspace)
    page_directory = contained_path(settings.page_dir / workspace / document.id, settings.page_dir / workspace)
    if original.exists():
        original.unlink()
    if page_directory.exists():
        shutil.rmtree(page_directory)
    if not store.delete(document.id, workspace):
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(status_code=204)


def process_document(document_id: str, workspace: str) -> None:
    document = store.get(document_id, workspace)
    if not document:
        return
    try:
        document.status, document.progress = "parsing", 20
        store.put(document)
        document.pages = parse_document(Path(document.storage_path), document.mime_type, settings.page_dir / workspace / document.id)
        document.page_count, document.progress = len(document.pages), 58
        document.status = "classifying"
        store.put(document)
        content = "\n".join(page.text for page in document.pages)[:18000]
        document.classification = llm.classify(document.name, content)
        document.status, document.progress = "indexing", 82
        store.put(document)
        document.status, document.progress = "indexed", 100
        store.put(document)
    except Exception as exc:
        document.status, document.error = "failed", str(exc)[:300]
        store.put(document)


@app.get("/api/documents/{document_id}/pages/{page_number}/image")
def page_image(document_id: str, page_number: int, workspace: str = Query(...), expires: int = Query(...), signature: str = Query(...)) -> FileResponse:
    verify_page_signature(workspace, document_id, page_number, expires, signature, settings.app_signing_secret)
    document = store.get(document_id, workspace_id(workspace))
    page = next((item for item in document.pages if item.page_number == page_number), None) if document else None
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(page.image_path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"})


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request, x_workspace_id: str | None = Header(default=None), x_internal_token: str | None = Header(default=None)) -> ChatResponse:
    authorize(x_internal_token)
    workspace = workspace_id(x_workspace_id)
    client = request.client.host if request.client else "unknown"
    rate_limiter.check(f"chat:{workspace}:{client}", settings.chat_requests_per_minute)
    question = payload.messages[-1].content
    history = "\n".join(f"{turn.role}: {turn.content}" for turn in payload.messages[:-1])
    plan = llm.plan_search(question, history)
    matches = retrieve(plan.search_queries, store.list(workspace))
    evidence, allowed_tokens = evidence_block(matches)
    answer = llm.answer(question, history, evidence, allowed_tokens) if matches else "I couldn't find enough relevant evidence in the indexed documents."
    citations = validated_citations(answer, matches, signed_page_url)
    if matches and not citations:
        answer = llm._fallback_answer(evidence)
        citations = validated_citations(answer, matches, signed_page_url)
    return ChatResponse(id=str(uuid4()), content=answer, citations=citations)
