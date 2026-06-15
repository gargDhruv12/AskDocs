from pathlib import Path
import fitz
import pdfplumber
from PIL import Image, ImageOps
import pytesseract
from .models import PageRecord

Image.MAX_IMAGE_PIXELS = 40_000_000


def _ocr(image: Image.Image) -> str:
    try:
        grayscale = ImageOps.autocontrast(ImageOps.grayscale(image))
        return pytesseract.image_to_string(grayscale, config="--psm 6").strip()
    except (pytesseract.TesseractNotFoundError, RuntimeError):
        return ""


def parse_document(source: Path, mime_type: str, page_dir: Path) -> list[PageRecord]:
    page_dir.mkdir(parents=True, exist_ok=True)
    if mime_type == "application/pdf":
        return _parse_pdf(source, page_dir)
    if mime_type.startswith("image/"):
        image = Image.open(source)
        image.verify()
        image = Image.open(source).convert("RGB")
        if image.width * image.height > Image.MAX_IMAGE_PIXELS:
            raise ValueError("Image dimensions exceed the processing limit")
        image_path = page_dir / "1.jpg"
        image.save(image_path, "JPEG", quality=88, optimize=True)
        return [PageRecord(page_number=1, text=_ocr(image), image_path=str(image_path))]
    text = source.read_text(encoding="utf-8", errors="replace")
    image = Image.new("RGB", (1240, 1754), "white")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    draw.multiline_text((90, 90), text[:9000], fill="#17211c", spacing=8)
    image_path = page_dir / "1.jpg"
    image.save(image_path, "JPEG", quality=88)
    return [PageRecord(page_number=1, text=text, image_path=str(image_path))]


def _parse_pdf(source: Path, page_dir: Path) -> list[PageRecord]:
    records: list[PageRecord] = []
    pdf = fitz.open(source)
    if pdf.page_count > 200:
        raise ValueError("Documents are limited to 200 pages")
    with pdfplumber.open(source) as plumber_pdf:
        for index, page in enumerate(pdf):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            image_path = page_dir / f"{index + 1}.jpg"
            pixmap.save(image_path)
            text = page.get_text("text").strip()
            if len(text) < 40:
                text = _ocr(Image.open(image_path))
            tables = plumber_pdf.pages[index].extract_tables() or []
            records.append(PageRecord(page_number=index + 1, text=text, image_path=str(image_path), tables=tables))
    pdf.close()
    return records
