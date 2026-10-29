"""Atomic prototype document uploads: bytes and metadata, with server scope checks."""
import base64
import binascii
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from .accounts import _user
from .auth import get_verified_subject
from .audit import append_event
from .outbox import enqueue
from .portal_snapshot import snapshot
from .storage import store_file, retrieve_file, validate_file_content, validate_file_name, file_scan_evidence
from .transactions import write_transaction

router=APIRouter(tags=['portal files'])
class UploadFile(BaseModel):
 document_id: UUID | None=None
 institution_id: UUID
 application_id: UUID | None=None
 document_type: str=Field(min_length=1,max_length=100)
 file_name: str=Field(min_length=1,max_length=255)
 mime_type: str
 content_base64: str=Field(min_length=1,max_length=14_000_000)
 issue_date: date | None=None
 expiry_date: date | None=None
 expected_version: int | None=None
 issuer: str=Field(default='',max_length=255)
 reference: str=Field(default='',max_length=255)

@router.post('/portal/documents',status_code=201)
def upload_document(payload:UploadFile,request:Request,subject:Annotated[str,Depends(get_verified_subject)]):
 _user(request,subject)
 validate_file_name(payload.file_name,payload.mime_type)
 try: content=base64.b64decode(payload.content_base64,validate=True)
 except (ValueError,binascii.Error): raise HTTPException(400) from None
 checksum,size=validate_file_content(content,payload.mime_type,10*1024*1024)
 if payload.issue_date and payload.expiry_date and payload.expiry_date<payload.issue_date:raise HTTPException(400)
 with write_transaction(request.app.state.settings.database_write_url,subject) as conn:
  data=snapshot(conn,subject)
  actor=next((u for u in data['users'] if u['id']==subject),None)
  if not actor or not any(a['role']=='INSTITUTION' for a in actor['assignments']):raise HTTPException(403)
  with conn.cursor(row_factory=dict_row) as cur:
   cur.execute("SELECT 1 FROM user_role_assignments a JOIN roles r ON r.id=a.role_id WHERE a.user_id=%s AND r.role_code LIKE '%%_VIEWER' AND a.status='active'",(subject,))
   if cur.fetchone():raise HTTPException(403)
   institution=next((i for i in data['institutions'] if i['id']==str(payload.institution_id)),None)
   if not institution:raise HTTPException(404)
   if payload.application_id and not any(a['id']==str(payload.application_id) and a['institutionId']==str(payload.institution_id) for a in data['applications']):raise HTTPException(404)
   cur.execute('SELECT id,supports_expiry FROM document_types WHERE document_type_code=%s OR document_type_code=%s',(payload.document_type,'DEMO-'+payload.document_type))
   kind=cur.fetchone()
   if not kind:raise HTTPException(400,detail='Unknown document type')
   if payload.expiry_date and not kind['supports_expiry']:raise HTTPException(400,detail='This document category does not expire')
   doc_id=payload.document_id or uuid4(); ver_id=uuid4(); now=datetime.now(timezone.utc)
   if payload.document_id:
    if not any(d['id']==str(doc_id) and d['institutionId']==str(payload.institution_id) for d in data['documents']):raise HTTPException(404)
    cur.execute('SELECT version,document_type_id FROM documents WHERE id=%s FOR UPDATE',(doc_id,)); old=cur.fetchone()
    if payload.expected_version is None or old['version']!=payload.expected_version:raise HTTPException(412)
    if old['document_type_id']!=kind['id']:raise HTTPException(400)
    cur.execute('SELECT COALESCE(MAX(version_number),0)+1 AS n FROM document_versions WHERE document_id=%s',(doc_id,)); number=cur.fetchone()['n']
   else:
    number=1
    cur.execute("INSERT INTO documents(id,institution_id,application_id,document_type_id,document_scope,status,created_by,updated_by,version) VALUES(%s,%s,%s,%s,%s,'active',%s,%s,1)",(doc_id,payload.institution_id,payload.application_id,kind['id'],'application' if payload.application_id else 'institution',subject,subject))
   key='prototype/'+str(doc_id)+'/'+str(ver_id)
   store_file(key,content)
   cur.execute("INSERT INTO document_versions(id,document_id,version_number,object_key,file_name,mime_type,size_bytes,sha256_hash,uploaded_by,uploaded_at,issue_date,expiry_date,verification_status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')",(ver_id,doc_id,number,key,payload.file_name,payload.mime_type,size,checksum,subject,now,payload.issue_date,payload.expiry_date))
   cur.execute('UPDATE documents SET current_version_id=%s,version=version+%s,updated_by=%s,updated_at=%s WHERE id=%s',(ver_id,1 if payload.document_id else 0,subject,now,doc_id))
   cur.execute('UPDATE documents SET issuer=%s,reference=%s WHERE id=%s',(payload.issuer,payload.reference,doc_id))
   scan=file_scan_evidence(key)
   cur.execute('INSERT INTO document_file_scans(document_version_id,status,evidence) VALUES(%s,%s,%s)',(ver_id,scan['status'],__import__('psycopg.types.json',fromlist=['Jsonb']).Jsonb(scan)))
   metadata={'document_id':str(doc_id),'version_id':str(ver_id),'sha256':checksum,'size_bytes':size,'issuer':payload.issuer,'reference':payload.reference,'scan_status':scan['status']}
   append_event(cur,actor_id=UUID(subject),action='DOCUMENT_VERSION_UPLOADED',entity_type='document',entity_id=doc_id,correlation_id=getattr(request.state,'correlation_id',None),reason='Prototype upload; verification and malware scan pending',metadata=metadata)
   enqueue(cur,event_type='DOCUMENT_VERSION_UPLOADED',entity_type='document',entity_id=doc_id,payload=metadata)
 return {'id':str(doc_id),'version_id':str(ver_id),'message':'File and immutable metadata saved. Human verification remains pending.'}
