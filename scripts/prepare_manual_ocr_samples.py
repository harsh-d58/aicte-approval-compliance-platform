"""Prepare faithful pixel-only OCR controls from a public official PDF.

This artifact utility never changes the application OCR implementation or embeds
the answer key in the PNG/PDF. Requires Pillow, pypdf, pypdfium2 and reportlab.
"""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
from pypdf import PdfReader
import pypdfium2 as pdfium
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "ocr_manual_test"
SOURCE = OUT / "official_delhi_fire_safety_certificate.pdf"
SOURCE_URL = "https://dfs.delhi.gov.in/sites/default/files/circulars-orders/52026021801098_firesafetycertificate.pdf"
PAGE_URL = "https://dfs.delhi.gov.in/node/15964"
SOURCE_SHA256 = "6500b999d34d50aef1da3e7f1be5ec3e9c6acd94e28078416392b9fae4d2496c"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    assert SOURCE.exists(), "Download the unchanged official source PDF first"
    assert digest(SOURCE) == SOURCE_SHA256, "Source changed; inspect and update provenance explicitly"
    OUT.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(str(SOURCE))
    original = PdfReader(SOURCE)
    scanned = OUT / "official_certificate_image_only.pdf"
    writer = canvas.Canvas(str(scanned), pageCompression=1)
    writer.setTitle("Image-only OCR test derivative of public Delhi Fire Service certificate")
    writer.setAuthor("OCR evaluation artifact; source: Department of Delhi Fire Service")
    images = []
    for index, page in enumerate(document):
        rendered = page.render(scale=220 / 72).to_pil().convert("RGB")
        # Copy pixels into a fresh image to discard embedded source metadata.
        clean = Image.new("RGB", rendered.size, "white")
        clean.paste(rendered)
        image_path = OUT / f"official_certificate_page_{index + 1}.png"
        clean.save(image_path, format="PNG")
        images.append(image_path)
        width = float(original.pages[index].mediabox.width)
        height = float(original.pages[index].mediabox.height)
        writer.setPageSize((width, height))
        writer.drawImage(ImageReader(clean), 0, 0, width=width, height=height)
        writer.showPage()
    writer.save()
    document.close()

    raster = PdfReader(scanned)
    assert len(raster.pages) == len(original.pages)
    assert all(not (p.extract_text() or "").strip() for p in raster.pages), "Raster control must have no hidden text layer"
    assert all(len(p.images) >= 1 for p in raster.pages), "Every raster PDF page must contain pixels"
    for path in images:
        with Image.open(path) as image:
            assert not getattr(image, "text", {}), "PNG contains an embedded answer layer"
            assert not image.getexif(), "PNG contains EXIF"
    assert digest(SOURCE) == SOURCE_SHA256

    expected = {
        "document_type": "FIRE SAFETY CERTIFICATE",
        "government": "Government of National Capital Territory of Delhi",
        "department": "Delhi Fire Service",
        "application_id": "52026021801098",
        "reference_label": "Application ID",
        "issue_date_iso": "2026-03-06",
        "printed_issue_date": "06-03-2026",
        "inspection_date_iso": "2026-02-25",
        "institution": "Hari Vidhya Bhawan School",
        "address": "K-II/600, Sangam Vihar, New Delhi - 110080",
        "validity_duration_years": 3,
        "explicit_expiry_date": None,
        "expiry_note": "The document prints a start date and three-year duration, not a separately labelled expiry date. Do not claim an explicit extracted expiry date.",
        "named_officer": "A.K.Malik",
        "officer_designation": "Dy.Chief Fire Officer",
        "signature_note": "The source says it is computer generated and does not require signature.",
        "provenance": "Human labels from the rendered original; this answer key is separate from upload files."
    }
    (OUT / "expected_fields.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "retrieved_on": "2026-10-29", "source_page": PAGE_URL, "source_pdf": SOURCE_URL,
        "source_unchanged": True, "render_dpi": 220,
        "pdf_pages": len(original.pages), "original_has_text_layer": any((p.extract_text() or "").strip() for p in original.pages),
        "image_only_pdf_has_text_layer": False, "png_has_embedded_answers": False,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": digest(p)} for p in [SOURCE, *images, scanned]]
    }
    (OUT / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print("Verified unchanged source, clean PNG pixels and image-only PDF. VERDICT: PASS")


if __name__ == "__main__":
    main()
