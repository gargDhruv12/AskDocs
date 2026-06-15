from app.models import DocumentRecord, PageRecord
from app.rag import evidence_block, retrieve, validated_citations


def test_retrieval_and_citations_are_page_grounded():
    document = DocumentRecord(id="doc1", workspace_id="team", name="solar-report.pdf", storage_path="x", mime_type="application/pdf", status="indexed", pages=[PageRecord(page_number=3, text="Solar output increased by 24 percent in 2025.", image_path="page.jpg")])
    matches = retrieve("How much did solar output increase?", [document])
    evidence, tokens = evidence_block(matches)
    assert tokens == ["[solar-report.pdf, p. 3]"]
    citations = validated_citations(f"It increased by 24 percent {tokens[0]}", matches, lambda _document, page: f"/signed/{page}")
    assert citations[0].page_number == 3
    assert citations[0].image_url == "/signed/3"
    assert "24 percent" in evidence


def test_empty_collection_returns_no_matches():
    assert retrieve("unknown question", []) == []


def test_structured_table_cells_are_retrievable():
    document = DocumentRecord(id="doc2", workspace_id="team", name="operations.pdf", storage_path="x", mime_type="application/pdf", status="indexed", pages=[PageRecord(page_number=1, text="Quarterly performance", image_path="page.jpg", tables=[[["Team", "Target", "Actual"], ["Delivery", "95%", "96.4%"]]])])
    matches = retrieve("What was actual delivery performance?", [document])
    assert matches
    assert "96.4%" in matches[0].text


def test_fabricated_citation_is_not_exposed():
    document = DocumentRecord(id="doc3", workspace_id="team", name="real.pdf", storage_path="x", mime_type="application/pdf", status="indexed", pages=[PageRecord(page_number=1, text="Verified content", image_path="page.jpg")])
    matches = retrieve("verified content", [document])
    assert validated_citations("Unsupported [fake.pdf, p. 99]", matches) == []


def test_only_cited_relevant_document_is_exposed():
    relevant = DocumentRecord(id="relevant", workspace_id="team", name="resume.pdf", storage_path="x", mime_type="application/pdf", status="indexed", pages=[PageRecord(page_number=1, text="Dhruv studies information technology.", image_path="resume.jpg")])
    unrelated = DocumentRecord(id="unrelated", workspace_id="team", name="clinical.pdf", storage_path="x", mime_type="application/pdf", status="indexed", pages=[PageRecord(page_number=1, text="A clinical trial enrolled participants.", image_path="clinical.jpg")])
    matches = retrieve("Tell me about Dhruv", [relevant, unrelated])
    citations = validated_citations("Dhruv studies information technology. [resume.pdf, p. 1]", matches)
    assert [citation.document_name for citation in citations] == ["resume.pdf"]
