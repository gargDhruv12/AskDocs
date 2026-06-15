from pathlib import Path
import fitz
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples"
OUT.mkdir(exist_ok=True)


def make_pdf(name: str, title: str, pages: list[str], table: list[list[str]] | None = None) -> None:
    document = fitz.open()
    for page_index, body in enumerate(pages):
        page = document.new_page(width=595, height=842)
        page.draw_rect(fitz.Rect(0, 0, 595, 82), color=(0.12, 0.35, 0.26), fill=(0.12, 0.35, 0.26))
        page.insert_text((44, 49), title, fontsize=20, color=(1, 1, 1), fontname="hebo")
        page.insert_text((44, 70), f"Evidence sample / page {page_index + 1}", fontsize=8, color=(0.82, 0.9, 0.85))
        y = 116
        for paragraph in body.split("\n"):
            page.insert_textbox(fitz.Rect(44, y, 550, y + 100), paragraph, fontsize=11, lineheight=1.35, color=(0.09, 0.13, 0.11))
            y += 78
        if table and page_index == len(pages) - 1:
            y += 10
            row_h, widths = 32, [170, 120, 120]
            for row_index, row in enumerate(table):
                x = 44
                for column_index, value in enumerate(row):
                    rect = fitz.Rect(x, y + row_index * row_h, x + widths[column_index], y + (row_index + 1) * row_h)
                    fill = (0.86, 0.91, 0.87) if row_index == 0 else (0.97, 0.97, 0.94)
                    page.draw_rect(rect, color=(0.55, 0.63, 0.57), fill=fill, width=0.6)
                    page.insert_textbox(rect + (7, 8, -4, -4), value, fontsize=8.5, color=(0.09, 0.13, 0.11))
                    x += widths[column_index]
    document.save(OUT / name)
    document.close()


def make_scanned_pdf() -> None:
    image = Image.new("RGB", (1240, 1754), "#eee9de")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 34)
    small = ImageFont.truetype("arial.ttf", 25)
    draw.text((90, 90), "FIELD INSPECTION NOTE", fill="#28352e", font=font)
    lines = [
        "Site: North Ridge Solar Array", "Inspection date: 18 May 2026",
        "Finding: inverter seven showed intermittent heat warnings.",
        "Action: replace the cooling fan before 30 May 2026.",
        "Priority: high. Estimated downtime: two hours."
    ]
    for index, line in enumerate(lines):
        draw.text((100, 190 + index * 75), line, fill="#303530", font=small)
    draw.rectangle((70, 70, 1170, 760), outline="#8c877c", width=3)
    png = OUT / "field-inspection-scan.png"
    image.save(png)
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_image(page.rect, filename=str(png))
    # Invisible text makes the sample searchable even when local Tesseract is unavailable.
    page.insert_text((30, 820), "North Ridge Solar Array inverter seven heat warning replace cooling fan priority high", fontsize=1, render_mode=3)
    document.save(OUT / "field-inspection-scan.pdf")
    document.close()


make_pdf("renewable-energy-outlook.pdf", "Renewable Energy Outlook", [
    "Executive summary\nSolar generation increased by 24 percent during 2025, driven by lower module prices and faster permitting.",
    "Regional findings\nWestern sites produced 18 percent more energy than forecast. Grid interconnection remains the largest delivery risk."
], [["Metric", "2024", "2025"], ["Solar output", "8.1 TWh", "10.0 TWh"], ["Storage capacity", "2.4 GWh", "3.7 GWh"]])
make_pdf("vendor-risk-review.pdf", "Vendor Risk Review", [
    "CONFIDENTIAL\nThe review covers identity controls, data retention, incident response, and subcontractor exposure.",
    "Decision\nAster Cloud is conditionally approved. The vendor must reduce backup retention from 365 days to 90 days before production access."
])
make_pdf("employee-travel-policy.pdf", "Employee Travel Policy", [
    "Employees may book economy airfare for journeys under six hours. Manager approval is required for exceptions.",
    "Receipts are required for expenses above $25. Reimbursement requests must be filed within 30 days."
])
make_pdf("clinical-trial-brief.pdf", "Clinical Trial Brief", [
    "RESTRICTED MEDICAL INFORMATION\nThe anonymized pilot enrolled 84 participants. No government identifiers are included in this sample.",
    "Outcome\nThe primary endpoint improved by 11.2 percent compared with baseline. Two serious adverse events were reviewed and found unrelated."
])
make_pdf("quarterly-operations.pdf", "Quarterly Operations", [
    "Quarter two delivery performance reached 96.4 percent. Customer support response time improved from 4.8 hours to 2.9 hours."
], [["Team", "Target", "Actual"], ["Delivery", "95%", "96.4%"], ["Support", "3.5 hr", "2.9 hr"]])
make_scanned_pdf()
print(f"Created samples in {OUT}")

