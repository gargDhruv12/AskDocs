from pathlib import Path
from app.parser import parse_document


SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def test_pdf_parser_stores_page_images_and_structured_tables(tmp_path):
    pages = parse_document(SAMPLES / "quarterly-operations.pdf", "application/pdf", tmp_path / "pages")
    assert len(pages) == 1
    assert Path(pages[0].image_path).exists()
    assert pages[0].tables
    assert pages[0].tables[0][0] == ["Team", "Target", "Actual"]


def test_scanned_pdf_remains_searchable(tmp_path):
    pages = parse_document(SAMPLES / "field-inspection-scan.pdf", "application/pdf", tmp_path / "scan")
    assert "inverter seven" in pages[0].text.lower()

