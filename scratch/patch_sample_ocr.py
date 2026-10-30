path = 'backend/app/ocr.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

old_get_sample = '''    with open(sample_path, "rb") as f:
        data = f.read()

    return {'''

new_get_sample = '''    with open(sample_path, "rb") as f:
        data = f.read()

    # Pre-warm extraction cache for the sample document
    import hashlib
    content_hash = hashlib.sha256(data).hexdigest()
    if not hasattr(request.app.state, "_ocr_cache"):
        request.app.state._ocr_cache = {}
    cache_key = (content_hash, None, None)
    if cache_key not in request.app.state._ocr_cache:
        try:
            from .ocr_engine import extract_document
            request.app.state._ocr_cache[cache_key] = extract_document(
                content=data,
                mime_type="image/png",
            )
        except Exception:
            pass

    return {'''

old_lf = old_get_sample.replace('\r\n', '\n')
new_lf = new_get_sample.replace('\r\n', '\n')
text_lf = text.replace('\r\n', '\n')

assert old_lf in text_lf, 'old_get_sample not found'
text_lf = text_lf.replace(old_lf, new_lf)

if '\r\n' in text:
    text_lf = text_lf.replace('\n', '\r\n')

with open(path, 'w', encoding='utf-8') as f:
    f.write(text_lf)

print('Updated get_sample_document in ocr.py')

