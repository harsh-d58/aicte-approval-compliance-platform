with open("backend/app/ocr.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """    candidates=list((root / "output" / "pdf" / "ocr_manual_test").glob("*.png"))
    sample_path=candidates[0] if candidates else root / "missing-government-sample.png" """

replacement = """    custom_sample = root / "sample_documents" / "aicte_fire_safety_certificate.png"
    if custom_sample.exists():
        sample_path = custom_sample
    else:
        candidates = list((root / "output" / "pdf" / "ocr_manual_test").glob("*.png"))
        sample_path = candidates[0] if candidates else root / "missing-government-sample.png" """

if "candidates=list((root / \"output\"" in text:
    import re
    text = re.sub(
        r'candidates\s*=\s*list\(\(root\s*/\s*"output"\s*/\s*"pdf"\s*/\s*"ocr_manual_test"\)\.glob\("\*\.png"\)\)\s*\n\s*sample_path\s*=\s*candidates\[0\]\s*if\s*candidates\s*else\s*root\s*/\s*"missing-government-sample\.png"',
        '''custom_sample = root / "sample_documents" / "aicte_fire_safety_certificate.png"
    if custom_sample.exists():
        sample_path = custom_sample
    else:
        candidates = list((root / "output" / "pdf" / "ocr_manual_test").glob("*.png"))
        sample_path = candidates[0] if candidates else root / "missing-government-sample.png"''',
        text
    )

with open("backend/app/ocr.py", "w", encoding="utf-8") as f:
    f.write(text)

print("backend/app/ocr.py sample path updated!")

