"""Decision outcomes and persisted prerequisites shared by route checks."""
from fastapi import HTTPException


ALIASES = {
    'approve': 'approve', 'approval': 'approve', 'approved': 'approve',
    'reject': 'reject', 'rejection': 'reject', 'rejected': 'reject',
    'close': 'close', 'closure': 'close', 'closed': 'close',
    'withdraw': 'withdraw', 'withdrawal': 'withdraw', 'withdrawn': 'withdraw',
}


def decision_outcome(kind, status):
    canonical = ALIASES.get(kind.strip().lower())
    if not canonical:
        raise HTTPException(422, detail='Unsupported decision outcome')
    if status == 'draft':
        return canonical, None
    expected = {'approve':'approved', 'reject':'rejected', 'close':'approved', 'withdraw':'withdrawn'}[canonical]
    if status != expected:
        raise HTTPException(422, detail='Decision status must match its selected outcome')
    return canonical, {'approve':'approved', 'reject':'rejected', 'close':'closed', 'withdraw':'withdrawn'}[canonical]


def check_decision_prerequisites(cur, app, kind, outcome):
    if kind == 'close':
        if app['status'] != 'approved':
            raise HTTPException(409, detail='Only an approved application can be closed')
        cur.execute('SELECT id,status FROM public.compliance_conditions WHERE application_id=%s ORDER BY id FOR UPDATE', (app['id'],))
        if any(condition['status'] != 'closed' for condition in cur.fetchall()):
            raise HTTPException(409, detail='Close every verified approval condition before closing the application')
        return
    if app['status'] in ('approved', 'rejected', 'closed', 'withdrawn'):
        raise HTTPException(409, detail='This application already has a final decision')
    if app.get('stage_type') != 'decision':
        raise HTTPException(409, detail='Complete the configured review route before recording a decision')
    if outcome not in ('approved', 'rejected'):
        return
    cur.execute("SELECT count(*) AS count FROM public.deficiency_items i JOIN public.deficiency_notices n ON n.id=i.deficiency_notice_id WHERE n.application_id=%s AND i.resolution_status NOT IN ('accepted','waived')", (app['id'],))
    if cur.fetchone()['count']:
        raise HTTPException(409, detail='Resolve every deficiency item before recording a decision')
    cur.execute("SELECT EXISTS(SELECT 1 FROM public.workflow_stages WHERE workflow_definition_id=%s AND stage_type='evc') AS required", (app['workflow_definition_id'],))
    if cur.fetchone()['required']:
        cur.execute("SELECT EXISTS(SELECT 1 FROM public.evc_visits v JOIN public.evc_reports r ON r.evc_visit_id=v.id JOIN public.meeting_record_versions m ON m.id=r.current_version_id WHERE v.application_id=%s AND v.status='completed' AND r.report_status='approved' AND m.approval_status='approved' AND m.record_type='evc_report') AS ready", (app['id'],))
        if not cur.fetchone()['ready']:
            raise HTTPException(409, detail='Complete the EVC visit and approve its report before recording a decision')
