import re
import hashlib
import hmac
import time
import threading
from collections import defaultdict, deque
from pathlib import Path
from fastapi import HTTPException, UploadFile

ALLOWED_TYPES = {
    "application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg",
    "text/plain": ".txt"
}
MAGIC = {".pdf": b"%PDF", ".png": b"\x89PNG", ".jpg": b"\xff\xd8\xff"}


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        with self._lock:
            requests = self._requests[key]
            while requests and now - requests[0] >= window_seconds:
                requests.popleft()
            if len(requests) >= limit:
                retry_after = max(1, int(window_seconds - (now - requests[0])))
                raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.", headers={"Retry-After": str(retry_after)})
            requests.append(now)


def workspace_id(value: str | None) -> str:
    if not value or not re.fullmatch(r"[a-zA-Z0-9_-]{3,64}", value):
        raise HTTPException(status_code=401, detail="A valid workspace is required")
    return value


def require_internal_token(value: str | None, expected: str) -> None:
    if not value or not hmac.compare_digest(value, expected):
        raise HTTPException(status_code=401, detail="Invalid application credential")


def sign_page(workspace: str, document_id: str, page_number: int, secret: str, lifetime_seconds: int = 300) -> tuple[int, str]:
    expires = int(time.time()) + lifetime_seconds
    payload = f"{workspace}:{document_id}:{page_number}:{expires}".encode()
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return expires, signature


def verify_page_signature(workspace: str, document_id: str, page_number: int, expires: int, signature: str, secret: str) -> None:
    if expires < int(time.time()):
        raise HTTPException(status_code=401, detail="Page link has expired")
    payload = f"{workspace}:{document_id}:{page_number}:{expires}".encode()
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid page link")


async def validate_upload(file: UploadFile, max_bytes: int) -> tuple[bytes, str]:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.filename}")
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"{file.filename} exceeds the upload limit")
    if not data:
        raise HTTPException(status_code=400, detail=f"{file.filename} is empty")
    extension = ALLOWED_TYPES[file.content_type]
    signature = MAGIC.get(extension)
    if signature and not data.startswith(signature):
        raise HTTPException(status_code=400, detail=f"{file.filename} does not match its declared file type")
    return data, extension


def safe_display_name(name: str | None) -> str:
    cleaned = Path(name or "document").name.replace("\x00", "")
    return cleaned[:160] or "document"
