"""Inspect/apply only the additive completion migrations; never replay old phases."""
import argparse
from hashlib import sha256
from pathlib import Path
import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
FILES = ['020_document_file_invariants.sql', '030_access_workflow_history.sql',
         '031_typed_configuration_revisions.sql', '040_durable_communications.sql']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    config = dotenv_values(ROOT / '.env')
    with psycopg.connect(config['DATABASE_URL'], connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout = '3s'")
            cur.execute("SET LOCAL statement_timeout = '30s'")
            cur.execute("SELECT to_regclass('public.document_file_scans'), to_regclass('public.deficiency_item_responses'), to_regclass('public.configuration_revisions'), to_regclass('public.notification_delivery_jobs')")
            print('Existing migration markers:', cur.fetchone(), flush=True)
            cur.execute("SELECT document_id, count(*) FROM public.document_renewal_cases WHERE status NOT IN ('closed','cancelled','verified','completed','rejected') GROUP BY document_id HAVING count(*) > 1")
            duplicates = cur.fetchall()
            print('Duplicate active renewal groups:', len(duplicates), flush=True)
            if not args.apply:
                conn.rollback()
                return
            if duplicates:
                raise RuntimeError('Reconcile active renewal duplicates before unique-index migration; no rows changed')
            cur.execute('CREATE TABLE IF NOT EXISTS api_private.completion_migrations(name text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())')
            for name in FILES:
                source = (ROOT / 'backend' / 'migrations' / name).read_text(encoding='utf-8')
                digest = sha256(source.encode()).hexdigest()
                cur.execute('SELECT sha256 FROM api_private.completion_migrations WHERE name=%s', (name,))
                prior = cur.fetchone()
                if prior:
                    if prior[0] != digest:
                        raise RuntimeError('Applied migration checksum changed: ' + name)
                    print('Already applied:', name, flush=True)
                    continue
                cur.execute(source)
                cur.execute('INSERT INTO api_private.completion_migrations(name,sha256) VALUES(%s,%s)', (name, digest))
                print('Prepared:', name, flush=True)
        conn.commit()
        print('VERDICT: PASS — migration transaction committed', flush=True)


if __name__ == '__main__':
    main()
