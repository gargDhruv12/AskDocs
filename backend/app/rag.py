import re
from dataclasses import dataclass
from collections.abc import Callable
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import DocumentRecord, Citation


@dataclass
class Match:
    document: DocumentRecord
    page_number: int
    text: str
    score: float
    chunk_index: int = 0


def _chunks(text: str, target: int = 1100, overlap: int = 180) -> list[str]:
    normalized = " ".join(text.split())
    if len(normalized) <= target:
        return [normalized] if normalized else []
    chunks, start = [], 0
    while start < len(normalized):
        end = min(len(normalized), start + target)
        if end < len(normalized):
            boundary = normalized.rfind(". ", start + target // 2, end)
            if boundary > start:
                end = boundary + 1
        chunks.append(normalized[start:end])
        if end >= len(normalized):
            break
        start = max(start + 1, end - overlap)
    return chunks


def _page_content(page) -> str:
    table_text = []
    for table_index, table in enumerate(page.tables):
        rows = [" | ".join(cell or "" for cell in row) for row in table]
        table_text.append(f"TABLE {table_index + 1}:\n" + "\n".join(rows))
    return page.text + ("\n\n" + "\n\n".join(table_text) if table_text else "")


def retrieve(queries: str | list[str], documents: list[DocumentRecord], limit: int = 7) -> list[Match]:
    search_queries = [queries] if isinstance(queries, str) else queries
    candidates = [(document, page, index, chunk) for document in documents if document.status == "indexed" for page in document.pages for index, chunk in enumerate(_chunks(_page_content(page)))]
    if not candidates:
        return []
    corpus = search_queries + [chunk for _, _, _, chunk in candidates]
    matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=24000).fit_transform(corpus)
    query_count = len(search_queries)
    scores = cosine_similarity(matrix[:query_count], matrix[query_count:]).max(axis=0)
    ranked = sorted(zip(candidates, scores), key=lambda item: item[1], reverse=True)
    selected, seen = [], set()
    for ((document, page, chunk_index, chunk), score) in ranked:
        key = (document.id, page.page_number, chunk_index)
        if score < 0.025 or key in seen:
            continue
        selected.append(Match(document=document, page_number=page.page_number, text=chunk, score=float(score), chunk_index=chunk_index))
        seen.add(key)
        if len(selected) >= limit:
            break
    return selected


def evidence_block(matches: list[Match]) -> tuple[str, list[str]]:
    blocks, tokens = [], []
    for match in matches:
        token = f"[{match.document.name}, p. {match.page_number}]"
        tokens.append(token)
        blocks.append(f"SOURCE {token}\n{match.text[:3500]}")
    return "\n\n".join(blocks), tokens


def validated_citations(answer: str, matches: list[Match], image_url: Callable[[DocumentRecord, int], str] | None = None) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, int]] = set()
    for match in matches:
        token = f"[{match.document.name}, p. {match.page_number}]"
        key = (match.document.id, match.page_number)
        if token not in answer or key in seen:
            continue
        seen.add(key)
        excerpt = " ".join(match.text.split())[:260]
        url = image_url(match.document, match.page_number) if image_url else f"/api/documents/{match.document.id}/pages/{match.page_number}/image"
        citations.append(Citation(id=f"{match.document.id}-{match.page_number}", document_id=match.document.id, document_name=match.document.name, page_number=match.page_number, excerpt=excerpt, image_url=url))
    return citations
