from pathlib import Path
p=Path('backend/app/ocr_engine.py')
s=p.read_text(); s=s[:s.index('def extract_from_image_bytes')]+'''MAX_PAGES = 40
MAX_PIXELS = 24_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


@lru_cache(maxsize=1)
def _rapid_engine():
    from rapidocr import RapidOCR
    # Bundled ONNX models; no fixture text or metadata inputs.
    return RapidOCR()


def engine_readiness() -> dict[str, Any]:
    backend = os.environ.get("OCR_ENGINE", "auto").lower()
    if backend == "disabled":
        return {"ready": False, "engine": "disabled", "reason": "OCR disabled by configuration"}
    if backend in ("auto", "tesseract") and find_tesseract_cmd():
        try:
            pytesseract.pytesseract.tesseract_cmd = find_tesseract_cmd()
            return {"ready": True, "engine": "Tesseract", "version": str(pytesseract.get_tesseract_version())}
        except Exception:
            if backend == "tesseract":
                return {"ready": False, "engine": "Tesseract", "reason": "Native engine cannot execute"}
    if backend in ("auto", "rapidocr"):
        try:
            _rapid_engine()
            return {"ready": True, "engine": "RapidOCR ONNX", "version": package_version("rapidocr")}
        except Exception:
            return {"ready": False, "engine": "RapidOCR ONNX", "reason": "Recognition runtime or models unavailable"}
    return {"ready": False, "engine": backend, "reason": "Recognition engine unavailable"}


def _recognize(image: Image.Image) -> dict[str, Any]:
    if image.width * image.height > MAX_PIXELS:
        raise ValueError("Page exceeds pixel limit")
    image = ImageOps.exif_transpose(image)
    ready = engine_readiness()
    if not ready["ready"]:
        raise RuntimeError(ready["reason"])
    processed = preprocess_image(image)
    regions = []
    if ready["engine"] == "Tesseract":
        data = pytesseract.image_to_data(processed, lang=os.environ.get("OCR_LANGUAGES", "eng"),
            config="--psm 3", timeout=45, output_type=pytesseract.Output.DICT)
        lines = {}
        for i, word in enumerate(data.get("text", [])):
            if not word.strip(): continue
            confidence = float(data["conf"][i])
            confidence = confidence / 100 if confidence >= 0 else None
            regions.append({"text": word, "confidence": confidence,
                "box": [data["left"][i], data["top"][i], data["width"][i], data["height"][i]]})
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(key, []).append(word)
        text = "\\n".join(" ".join(words) for words in lines.values())
    else:
        import numpy as np
        result = _rapid_engine()(np.array(processed.convert("RGB")))
        texts = list(result.txts or [])
        scores = list(result.scores or [])
        boxes = result.boxes.tolist() if result.boxes is not None else []
        for i, word in enumerate(texts):
            regions.append({"text": word, "confidence": float(scores[i]) if i < len(scores) else None,
                "box": boxes[i] if i < len(boxes) else None})
        text = "\\n".join(texts)
    scores = [r["confidence"] for r in regions if r["confidence"] is not None]
    return {"text": text, "confidence": sum(scores) / len(scores) if scores else None,
        "engine": ready["engine"], "version": ready["version"], "regions": regions}


def extract_from_image_bytes(content: bytes) -> tuple[str, float | None, str, str | None]:
    """Compatibility wrapper: returns no text/confidence when recognition is unavailable."""
    try:
        with Image.open(BytesIO(content)) as image:
            result = _recognize(image)
        return result["text"], result["confidence"], result["engine"], result["version"]
    except Exception:
        return "", None, "OCR unavailable", None


def extract_document(content: bytes, mime_type: str, declared_issue_date: str | None = None,
                     declared_expiry_date: str | None = None) -> dict[str, Any]:
    """Bounded all-page extraction. PDF text and pixel recognition have distinct provenance."""
    started = datetime.now(timezone.utc).isoformat()
    pages = []
    errors = []
    if len(content) > 15 * 1024 * 1024:
        errors.append("Document exceeds 15 MB limit")
    else:
        try:
            if mime_type == "application/pdf":
                import pypdfium2 as pdfium
                reader = PdfReader(BytesIO(content))
                if reader.is_encrypted: raise ValueError("Encrypted PDFs require an unencrypted source")
                if len(reader.pages) > MAX_PAGES: raise ValueError("PDF exceeds 40 page limit")
                rendered = None
                try:
                    for index, page in enumerate(reader.pages):
                        text = (page.extract_text() or "").strip()
                        # Render image-bearing/mixed pages so no scanned region is silently omitted.
                        has_images = bool(list(page.images))
                        if has_images or not text:
                            if rendered is None: rendered = pdfium.PdfDocument(content)
                            pdf_page = rendered[index]
                            width, height = pdf_page.get_size()
                            scale = min(2.5, (MAX_PIXELS / max(1, width * height)) ** 0.5)
                            bitmap = pdf_page.render(scale=scale)
                            image = bitmap.to_pil()
                            try:
                                recognized = _recognize(image)
                                pages.append({"page": index + 1, "mode": "pixel_ocr", **recognized,
                                    "dpi": round(scale * 72), "pdf_text_layer": text or None})
                            except Exception as error:
                                errors.append(f"Page {index + 1}: {error}")
                                pages.append({"page": index + 1, "mode": "unavailable", "text": text,
                                    "confidence": None, "engine": "PDF text layer" if text else "Unavailable",
                                    "version": package_version("pypdf"), "regions": []})
                            finally:
                                image.close(); bitmap.close(); pdf_page.close()
                        else:
                            pages.append({"page": index + 1, "mode": "pdf_text_layer", "text": text,
                                "confidence": None, "engine": "PDF text layer", "version": package_version("pypdf"), "regions": []})
                finally:
                    if rendered is not None: rendered.close()
            elif mime_type in ("image/png", "image/jpeg"):
                with Image.open(BytesIO(content)) as image:
                    if getattr(image, "n_frames", 1) != 1: raise ValueError("Multi-frame raster uploads are unsupported")
                    pages.append({"page": 1, "mode": "pixel_ocr", **_recognize(image)})
            else:
                raise ValueError(f"Unsupported MIME type for OCR: {mime_type}")
        except Exception as error:
            errors.append(str(error))
    source_text = "\\n\\n".join(p["text"] for p in pages if p["text"])
    pixel_pages = [p for p in pages if p["mode"] == "pixel_ocr"]
    measured = [p["confidence"] for p in pixel_pages if p["confidence"] is not None]
    confidence = sum(measured) / len(measured) if measured else None
    parsed = parse_statutory_fields(source_text)
    field_evidence = {}
    for name, value in parsed.items():
        field_evidence[name] = [{"page": p["page"], "mode": p["mode"], "value": value}
            for p in pages if value and value in p["text"]]
    status = "degraded" if errors and source_text else "unavailable" if errors else "completed"
    summary = {"overall_confidence": confidence, "source": ", ".join(dict.fromkeys(p["engine"] for p in pages)) or "Unavailable",
        "ocr_performed": bool(pixel_pages), "pages": pages, "source_sha256": sha256(content).hexdigest(),
        "started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
        "processing_parameters": {"max_pages": MAX_PAGES, "max_pixels_per_page": MAX_PIXELS, "date_locale": "en-IN", "exif_orientation": True}}
    fields = {"source_text": source_text or None, "source_error": "; ".join(errors) or None, **parsed,
        "declared_issue_date": declared_issue_date, "declared_expiry_date": declared_expiry_date,
        "field_evidence": field_evidence}
    return {"status": status, "source_text": source_text, "source_error": fields["source_error"],
        "engine_name": summary["source"], "engine_version": ", ".join(dict.fromkeys(str(p["version"]) for p in pages)) or None,
        "confidence_summary": summary, "extracted_fields": fields}
'''
p.write_text(s,encoding='utf-8')
