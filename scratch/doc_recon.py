from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
import importlib.util
p=Path('FINAL_PRD_COMPLETION_PLAN.md').read_text(encoding='utf-8')
for start,end in [('## CP05','## CP06'),('## CP08','## CP09')]: print(p[p.index(start):p.index(end)])
for f in ['frontend/app/portal-ui/OcrTester.tsx','frontend/app/portal-ui/DocumentPages.tsx','frontend/app/portal-ui/CompliancePages.tsx','backend/app/transactions.py','backend/migrations/006_phase3_documents_ocr.sql','backend/migrations/012_renewal_submission_version.sql']:
 print('\nFILE '+f+'\n'+Path(f).read_text(encoding='utf-8'))
for m in ['fitz','pypdfium2','rapidocr_onnxruntime','onnxruntime','cv2']: print(m, bool(importlib.util.find_spec(m)))
