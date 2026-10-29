"""Unit tests for Unified OCR engine, Pillow pre-processing, and statutory entity parsing."""

from io import BytesIO
import unittest
from unittest.mock import patch
from PIL.PngImagePlugin import PngInfo
from PIL import Image, ImageDraw

from backend.app.ocr_engine import (
    extract_document,
    extract_from_image_bytes,
    parse_statutory_fields,
    preprocess_image,
)


class OcrEngineTests(unittest.TestCase):
    def test_parse_statutory_fields_regex(self):
        sample_text = (
            "GOVERNMENT REGULATORY COMPLIANCE BUREAU\n"
            "FIRE SAFETY COMPLIANCE CERTIFICATE\n"
            "Certificate / Reference Number: FIRE-DEL-2024-9842\n"
            "Institution: DEMO Cedar Institute of Technology 001\n"
            "Issuing Authority: Directorate of Fire and Emergency Services, Delhi\n"
            "Issue Date: 2024-05-10\n"
            "Expiry Date: 2027-05-09\n"
        )
        parsed = parse_statutory_fields(sample_text)
        self.assertEqual(parsed["certificate_number"], "FIRE-DEL-2024-9842")
        self.assertEqual(parsed["extracted_issue_date"], "2024-05-10")
        self.assertEqual(parsed["extracted_expiry_date"], "2027-05-09")
        self.assertIn("Directorate of Fire", parsed["issuing_authority"])

    def test_parse_statutory_fields_fallback_pattern(self):
        text = "Compliance record approval: CERT-AICTE-2026-8849 authenticated."
        parsed = parse_statutory_fields(text)
        self.assertEqual(parsed["certificate_number"], "CERT-AICTE-2026-8849")

    def test_heading_and_application_id_are_not_certificate_number(self):
        parsed = parse_statutory_fields("FIRE SAFETY CERTIFICATE\nApplication ID. 52026021801098\nDated: 06-03-2026\nDELHI FIRE SERVICE")
        self.assertIsNone(parsed["certificate_number"])
        self.assertEqual(parsed["issuing_authority"], "DELHI FIRE SERVICE")
        self.assertEqual(parsed["extracted_issue_date"], "06-03-2026")
        self.assertIsNone(parsed["extracted_expiry_date"])

    def test_metadata_answers_never_substitute_for_ocr(self):
        metadata = PngInfo()
        metadata.add_text("Description", "Certificate Number: FAKE-2026-1234")
        buf = BytesIO()
        Image.new("RGB", (200, 100), "white").save(buf, format="PNG", pnginfo=metadata)
        with patch.dict("os.environ", {"OCR_ENGINE": "disabled"}):
            result = extract_document(buf.getvalue(), "image/png")
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["confidence_summary"]["ocr_performed"])
        self.assertIsNone(result["confidence_summary"]["overall_confidence"])
        self.assertIsNone(result["extracted_fields"]["certificate_number"])
        self.assertEqual(result["source_text"], "")

    def test_preprocess_image(self):
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "TEST COMPLIANCE", fill=(0, 0, 0))
        processed = preprocess_image(img)
        self.assertEqual(processed.mode, "L")
        self.assertEqual(processed.size, (200, 100))

    def test_extract_from_image_bytes(self):
        img = Image.new("RGB", (300, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "FIRE-DEL-2024-9842", fill=(0, 0, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        text, conf, eng_name, eng_ver = extract_from_image_bytes(png_bytes)
        self.assertTrue(len(text) > 0)
        self.assertGreaterEqual(conf, 0.10)
        self.assertTrue(len(eng_name) > 0)

    def test_extract_document_png(self):
        img = Image.new("RGB", (300, 150), color=(255, 255, 255))
        buf = BytesIO()
        img.save(buf, format="PNG")
        res = extract_document(buf.getvalue(), "image/png", declared_issue_date="2024-01-01")
        self.assertIn("extracted_fields", res)
        self.assertEqual(res["extracted_fields"]["declared_issue_date"], "2024-01-01")
        self.assertTrue(res["confidence_summary"]["ocr_performed"])

    def test_extract_document_unsupported_mime(self):
        res = extract_document(b"plain text", "text/plain")
        self.assertIn("Unsupported MIME type", res["source_error"])


if __name__ == "__main__":
    unittest.main()

