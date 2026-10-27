"""Read-only PRD schema inspection. Never prints credentials or application records."""
from datetime import datetime, timezone
from pathlib import Path
import json
import re

from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / 'backend/docs/database_audit.json'
prd = next(ROOT.glob('*PRD*.md')).read_text(encoding='utf-8')
entity_section = prd.split('## **5.2 ', 1)[1].split('# **6\\.', 1)[0]
expected = sorted(set(re.findall(r'^\|\s*`([a-z_]+)`\s*\|', entity_section, re.M)))
settings = dotenv_values(ROOT / 'backend/.env')
url = settings.get('DATABASE_URL')
result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'mode': 'read-only metadata', 'expected_prd_entities': expected}
try:
    if not url:
        raise ValueError('DATABASE_URL is unset')
    with psycopg.connect(url, connect_timeout=12, options='-c default_transaction_read_only=on -c statement_timeout=10000', row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('transaction_read_only') AS read_only, current_setting('server_version') AS server_version, (SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) AS ssl")
            result.update(cursor.fetchone())
            cursor.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') ORDER BY table_schema,table_name")
            result['tables'] = cursor.fetchall()
            cursor.execute("SELECT table_schema,table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY table_schema,table_name,ordinal_position")
            # Defaults may contain operational details; retain only their presence.
            result['columns'] = [{**{k: v for k,v in row.items() if k != 'column_default'}, 'has_default': row['column_default'] is not None} for row in cursor.fetchall() if row['table_name'] in expected]
            cursor.execute("SELECT tc.table_schema,tc.table_name,tc.constraint_name,tc.constraint_type,kcu.column_name,ccu.table_name AS referenced_table,ccu.column_name AS referenced_column FROM information_schema.table_constraints tc LEFT JOIN information_schema.key_column_usage kcu ON tc.constraint_schema=kcu.constraint_schema AND tc.constraint_name=kcu.constraint_name AND tc.table_name=kcu.table_name LEFT JOIN information_schema.constraint_column_usage ccu ON tc.constraint_schema=ccu.constraint_schema AND tc.constraint_name=ccu.constraint_name WHERE tc.table_schema NOT IN ('pg_catalog','information_schema') ORDER BY tc.table_schema,tc.table_name,tc.constraint_name")
            result['constraints'] = [row for row in cursor.fetchall() if row['table_name'] in expected]
            names = {row['table_name'] for row in result['tables']}
            result['matched_prd_entities'] = sorted(names.intersection(expected))
            result['missing_exact_prd_names'] = sorted(set(expected) - names)
            result['status'] = 'connected'
        connection.rollback()
except Exception as error:
    result.update(status='connection_failed', error_type=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None))
    description = str(error).lower()
    categories = {'timeout': ('timeout', 'timed out'), 'dns': ('getaddrinfo', 'resolve', 'name or service'), 'authentication': ('password authentication failed', 'authentication failed'), 'refused': ('connection refused', 'actively refused'), 'network_permission': ('permission denied', 'forbidden by its access permissions'), 'tls': ('ssl', 'certificate'), 'invalid_connection_string': ('invalid connection', 'invalid dsn', 'invalid integer', 'invalid uri')}
    result['error_categories'] = [name for name, fragments in categories.items() if any(fragment in description for fragment in fragments)]
    # Never persist or print exception text: it may include connection secrets.
target.parent.mkdir(exist_ok=True, parents=True)
target.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({k: result[k] for k in ('status','read_only','ssl','server_version','matched_prd_entities','missing_exact_prd_names','error_type','error_categories','sqlstate') if k in result}))
print('Sanitised metadata report: backend/docs/database_audit.json')
raise SystemExit(0 if result['status'] == 'connected' else 1)
