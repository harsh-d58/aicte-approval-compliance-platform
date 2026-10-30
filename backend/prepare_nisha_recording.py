"""Submit labelled demo evidence as Ananya; leave Nisha's review manual."""
import base64
import json
from pathlib import Path
import httpx
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

CASE='76e9a91b-343a-5d90-8f73-8f96b7b83603'
CONDITION='0def79df-6df3-401c-ba69-e8a9a1d93c9c'
OUT=Path('completion/nisha-recording-ready.json')

def main():
    proof={'application_id':CASE,'condition_id':CONDITION,'demo_only':True,'documents':[]}
    with httpx.Client(base_url='http://localhost:8000/api/v1',timeout=90) as client:
        response=client.post('/prototype/session',json={'persona_id':'user-institution'})
        response.raise_for_status();client.headers['Authorization']='Bearer '+response.json()['access_token']
        def call(method,path,body=None,key=None):
            r=client.request(method,path,json=body,headers={'Idempotency-Key':key} if key else None)
            assert r.status_code in (200,201),(path,r.status_code,r.text[:700])
            return r.json()
        data=call('GET','/portal/snapshot')
        condition=next(row for row in data['conditions'] if row['id']==CONDITION)
        app=next(row for row in data['applications'] if row['id']==CASE)
        assert app['number']=='AICTE-2026-DECISION-001' and app['status']=='APPROVED'
        assert condition['code']=='COND-1793341210646'
        existing=[row for row in data['evidence'] if row['conditionId']==CONDITION]
        if existing:
            latest=max(existing,key=lambda row:row['submissionNumber'])
            proof['submission']=latest
            proof['existing_verifications']=[row for row in data['verifications'] if row['evidenceId']==latest['id']]
            proof['condition_status']=condition['status']
            proof['action']='Existing evidence and any recorded determination preserved; no duplicates created'
            OUT.write_text(json.dumps(proof,indent=2),encoding='utf-8')
            print('VERDICT: PASS - existing Ananya evidence and Nisha review state preserved',flush=True)
            return
        assert condition['status']=='OPEN'
        for stem,title,detail in [
            ('DEMO_PWD_Structural_Attestation','Structural safety attestation - demo evidence',
             'Placeholder for the PWD Structural Safety Attestation required by the undertaking.'),
            ('DEMO_Geotagged_Photographs','Geotagged photographs - demo evidence',
             'Placeholder evidence index; no actual campus photographs or GPS claims included.')]:
            path=Path('sample_documents')/(stem+'.pdf')
            c=canvas.Canvas(str(path),pagesize=A4)
            c.setTitle(title);c.setFont('Helvetica-Bold',19);c.drawString(48,785,'SETU PROTOTYPE - DEMO ONLY')
            c.setFont('Helvetica-Bold',13);c.drawString(48,744,title)
            lines=['Application: AICTE-2026-DECISION-001','Condition: COND-1793341210646','Institution: Cedar Institute of Technology','',
                   detail,'','Created at the project owner request for a recorded compliance workflow.',
                   'This is not an official attestation, inspection record or safety certificate.',
                   'No public authority signature, seal or actual physical compliance is asserted.',
                   'Nisha Sen records the demonstration determination separately.']
            c.setFont('Helvetica',10)
            for i,line in enumerate(lines):c.drawString(48,710-i*23,line)
            c.save()
            # Render each real document locally for visual inspection.
            import fitz
            with fitz.open(path) as pdf:
                assert len(pdf)==1 and 'DEMO ONLY' in pdf[0].get_text()
                pdf[0].get_pixmap(matrix=fitz.Matrix(1,1)).save(str(path.with_suffix('.png')))
            existing_doc=next((doc for doc in data['documents'] if doc['applicationId']==CASE and any(v['fileName']==path.name for v in doc['versions'])),None)
            if existing_doc:
                saved={'id':existing_doc['id'],'version_id':existing_doc['currentVersionId']}
            else:
                saved=call('POST','/portal/documents',{'institution_id':condition['institutionId'],
                    'application_id':CASE,'document_type':'LIVE-EVIDENCE','file_name':path.name,
                    'mime_type':'application/pdf','content_base64':base64.b64encode(path.read_bytes()).decode(),
                    'issuer':'SETU prototype demonstration - not a public authority',
                    'reference':stem+'-RECORDING'})
            proof['documents'].append(saved)
            OUT.write_text(json.dumps(proof,indent=2),encoding='utf-8')
            print('PASS demo document uploaded as Ananya:',path.name,flush=True)
        submission=call('POST',f'/compliance-conditions/{CONDITION}/evidence-submissions',{
            'document_version_ids':[row['version_id'] for row in proof['documents']],
            'remarks':'Project owner requested recording preparation as Ananya. Both files are explicitly labelled synthetic demo evidence, not official attestation or actual photographs. Nisha will determine compliance manually.'},
            key='nisha-recording-evidence-'+CONDITION)
        proof['submission']=submission
        OUT.write_text(json.dumps(proof,indent=2),encoding='utf-8')
        print('PASS submitted both versions as Ananya; Nisha verification remains manual',flush=True)
    with httpx.Client(base_url='http://localhost:8000/api/v1',timeout=90) as client:
        r=client.post('/prototype/session',json={'persona_id':'user-compliance'});r.raise_for_status()
        client.headers['Authorization']='Bearer '+r.json()['access_token']
        r=client.get('/portal/snapshot');r.raise_for_status();data=r.json()
        condition=next(row for row in data['conditions'] if row['id']==CONDITION)
        evidence=next(row for row in data['evidence'] if row['id']==str(submission['id']))
        me=next(row for row in data['users'] if row['displayName']=='Nisha Sen')
        assert condition['status']=='EVIDENCE_SUBMITTED' and evidence['submittedBy']!=me['id']
        assert not any(row['evidenceId']==evidence['id'] for row in data['verifications'])
        proof['verified_as_nisha']={'status':condition['status'],'latest_evidence_unreviewed':True,'independent_submitter':True}
        OUT.write_text(json.dumps(proof,indent=2),encoding='utf-8')
        print('VERDICT: PASS - Nisha can now record the compliance determination',flush=True)

if __name__=='__main__':main()
