# Manual OCR test pack: actual public government certificate

## Source and files

The original is a public Delhi Fire Service certificate for Hari Vidhya Bhawan School, published by the Government of National Capital Territory of Delhi. It was downloaded unchanged on 29 October 2026.

- Source publication: https://dfs.delhi.gov.in/node/15964
- Original PDF: https://dfs.delhi.gov.in/sites/default/files/circulars-orders/52026021801098_firesafetycertificate.pdf
- `official_delhi_fire_safety_certificate.pdf`: unchanged official download; use as a PDF text-layer control.
- `official_certificate_page_1.png`: 220 DPI faithful rendering. No PNG Description/text/EXIF answer payload.
- `official_certificate_image_only.pdf`: faithful raster derivative with no searchable text layer. It requires actual OCR to recognize the page.
- `expected_fields.json`: separate human-readable answer key. **Do not upload this JSON as a document or feed it into the extraction engine.**
- `provenance.json`: source URLs, SHA-256 hashes and structural verification results.

The derivatives preserve the source page; they are not newly issued certificates and contain no changed institution, date, signature or reference. Use the record to test extraction, not as evidence that the test institution owns this certificate.

## Test procedure

1. Open the portal's document registry or OCR Testing Studio. Choose your own file instead of the built-in sample loader.
2. Upload `official_certificate_page_1.png` first. Record the engine name, actual OCR availability, extracted text, fields, confidence and elapsed time. Native Tesseract or another actual image-recognition engine is required.
3. Repeat with `official_certificate_image_only.pdf`. Every page must be recognized from pixels. A successful PDF text-layer read cannot explain a successful result here because the test pack verifies there is no text layer.
4. Upload the unchanged original PDF as a separate control. A text-layer extraction result is legitimate, but the UI should label that mode separately from image OCR.
5. Compare against `expected_fields.json`. At minimum, inspect the title, application ID `52026021801098`, issue date `06-03-2026`, institution and issuing department.
6. Check that the engine preserves the label **Application ID** instead of inventing a different certificate/reference number. Whitespace or punctuation normalization may be allowed if the source value remains inspectable.
7. The document states validity for **3 Years** from `06-03-2026`; it does not separately print a labelled expiry date. A derived expiry belongs to a policy calculation with provenance, not an asserted extracted date. Unknown values must remain unknown.
8. Save the result as an advisory check, refresh the page and sign in from another session. The actual file version, extraction, source mode and review state must remain persisted and authorized.
9. For a mismatch test, enter an intentionally different **declared** date/reference in your test record, keeping the source file unchanged. The system should show source-versus-declaration disagreement and request human review; it must not rewrite the extracted source to match the declaration.
10. Test engine failure by using an isolated environment with OCR disabled. The result must say unavailable/failed or require review. `ocr_performed=true`, invented 75-95% confidence, or copied PNG metadata does not pass.

## Current limitation established by the audit

At the last audit, native Tesseract was not detected and the built-in sample's embedded metadata supplied its answers. This new pack does not repair the application or claim that it currently passes. It makes a genuine pixel-recognition test possible once CP05 in the final plan is implemented.

## Artifact verification

The preparation utility checks the original checksum, page count, image objects, zero extractable text in the raster PDF and absence of embedded PNG answers. The final rendered page is also visually inspected. Reproduce with `scripts/prepare_manual_ocr_samples.py` using Pillow, pypdf, pypdfium2 and reportlab.
