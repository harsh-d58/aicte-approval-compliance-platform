import re

with open("backend/app/ocr_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

target = """    # 1. Certificate / Reference Number
    cert_pattern = re.compile(
        r"(?:Certificate|Registration|Sanction|Approval|Deed|Ref|Reference|Application\\s+ID)(?:\\s*(?:/|and)?\\s*(?:Reference|No\\.?|Number|#))*\\s*[.:\\-]\\s*([A-Za-z0-9\\/\\-_]{4,50})",
        re.IGNORECASE,
    )
    cert_match = cert_pattern.search(text)
    cert_num = cert_match.group(1).strip() if cert_match else None

    # If no explicit label matched, check for standard AICTE / state certificate codes
    if not cert_num:
        fallback_match = re.search(r"\\b([A-Z]{3,5}-[A-Z0-9]{3,5}-\\d{4}-\\d{3,6})\\b", text)
        if fallback_match:
            cert_num = fallback_match.group(1).strip()"""

replacement = """    # 1. Certificate / Reference Number
    cert_pattern = re.compile(
        r"(?:Certificate|Registration|Sanction|Approval|Deed|Ref|Reference|Application\\s+ID)(?:\\s*(?:/|and)?\\s*(?:Reference|No\\.?|Na\\.?|Number|#))*\\s*[.:\\-\\s]\\s*([A-Za-z0-9\\/\\-_]{4,50})",
        re.IGNORECASE,
    )
    cert_match = cert_pattern.search(text)
    cert_num = cert_match.group(1).strip() if cert_match else None

    # If no explicit label matched, check for standard AICTE / state certificate codes
    if not cert_num:
        fallback_match = re.search(r"\\b([A-Z]{3,5}-[A-Z0-9]{3,5}-\\d{4}-\\d{3,6})\\b", text)
        if fallback_match:
            cert_num = fallback_match.group(1).strip()
    if not cert_num:
        dfs_match = re.search(r"\\b(DFS\\/[A-Za-z0-9\\/\\-_]{4,40})\\b", text)
        if dfs_match:
            cert_num = dfs_match.group(1).strip()"""

if target in content:
    content = content.replace(target, replacement)
    print("Replaced successfully (LF)")
elif target.replace('\n', '\r\n') in content:
    content = content.replace(target.replace('\n', '\r\n'), replacement.replace('\n', '\r\n'))
    print("Replaced successfully (CRLF)")
else:
    print("Target not found directly, performing fallback regex replacement")
    content = re.sub(
        r'cert_pattern = re\.compile\(.*?\n\s+if fallback_match:\n\s+cert_num = fallback_match\.group\(1\)\.strip\(\)',
        '''cert_pattern = re.compile(
        r"(?:Certificate|Registration|Sanction|Approval|Deed|Ref|Reference|Application\\s+ID)(?:\\s*(?:/|and)?\\s*(?:Reference|No\\.?|Na\\.?|Number|#))*\\s*[.:\\-\\s]\\s*([A-Za-z0-9\\/\\-_]{4,50})",
        re.IGNORECASE,
    )
    cert_match = cert_pattern.search(text)
    cert_num = cert_match.group(1).strip() if cert_match else None

    if not cert_num:
        fallback_match = re.search(r"\\b([A-Z]{3,5}-[A-Z0-9]{3,5}-\\d{4}-\\d{3,6})\\b", text)
        if fallback_match:
            cert_num = fallback_match.group(1).strip()
    if not cert_num:
        dfs_match = re.search(r"\\b(DFS\\/[A-Za-z0-9\\/\\-_]{4,40})\\b", text)
        if dfs_match:
            cert_num = dfs_match.group(1).strip()''',
        content,
        flags=re.DOTALL
    )

with open("backend/app/ocr_engine.py", "w", encoding="utf-8") as f:
    f.write(content)

