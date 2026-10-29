"""Run recognition on unchanged government artifacts; never uses their labels as engine input."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding='utf-8')
from backend.app.ocr_engine import extract_document,engine_readiness
print(json.dumps(engine_readiness()))
results=[]
for path in sorted(Path('output/pdf/ocr_manual_test').glob('*')):
 if path.suffix.lower() not in ('.png','.pdf'): continue
 result=extract_document(path.read_bytes(),'application/pdf' if path.suffix=='.pdf' else 'image/png')
 results.append({'file':str(path),**result})
 print(path.name,result['status'],len(result['source_text']),result['confidence_summary']['ocr_performed'],result['source_error'])
 print(result['source_text'][:1400])
Path('completion/ocr-government-evidence.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
pixel=[r for r in results if r['file'].endswith('.png') or 'image_only' in r['file']]
passed=bool(pixel) and all(r['confidence_summary']['ocr_performed'] and len(r['source_text'])>150 for r in pixel)
print('VERDICT: PASS' if passed else 'VERDICT: FAIL -- Government pixel recognition incomplete')
sys.exit(0 if passed else 1)
