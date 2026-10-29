import psycopg
from psycopg.rows import dict_row
from dotenv import dotenv_values
from uuid import UUID
from datetime import datetime, timezone, timedelta
from backend.app.prototype import persona_subject
from backend.app.concurrency import lock_versioned, bump_version
from backend.app.workflows import evaluate_guard

env = dotenv_values('.env')
write_url = env.get('DATABASE_WRITE_URL')
subject = persona_subject("user-regional")
app_id = "73cc355b-a4f0-4f94-9060-4b483151938d"
to_stage_id = "0bae84c4-0f9f-5380-b121-44e8a7f68550"

with psycopg.connect(write_url, autocommit=True) as conn:
    with conn.transaction():
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT set_config('aicte.subject_id', %s, true)", (subject,))
            
            cur.execute(
                "SELECT a.id, a.status, a.current_stage_instance_id, a.workflow_definition_id, a.application_number, "
                "       si.workflow_stage_id as current_stage_id, a.version "
                "FROM public.applications a "
                "LEFT JOIN public.application_stage_instances si ON si.id = a.current_stage_instance_id "
                "WHERE a.id = %s",
                (app_id,),
            )
            app = cur.fetchone()
            print("App:", app)
            
            cur.execute(
                "SELECT id, guard_rule, transition_type, requires_authorisation "
                "FROM public.workflow_transitions "
                "WHERE workflow_definition_id = %s AND from_stage_id = %s AND to_stage_id = %s",
                (app["workflow_definition_id"], app["current_stage_id"], to_stage_id),
            )
            transition = cur.fetchone()
            print("Transition:", transition)
            
            cur.execute(
                "SELECT id, stage_code, stage_type, default_sla_days, owner_role_code FROM public.workflow_stages WHERE id = %s AND workflow_definition_id=%s",
                (to_stage_id, app["workflow_definition_id"]),
            )
            target_stage = cur.fetchone()
            print("Target stage:", target_stage)
            
            now = datetime.now(timezone.utc)
            # Complete current stage instance
            cur.execute(
                "UPDATE public.application_stage_instances "
                "SET status = 'completed', completed_at = %s "
                "WHERE id = %s",
                (now, app["current_stage_instance_id"]),
            )
            print("Completed current stage instance.")
            
            # Create new stage instance
            cur.execute(
                "INSERT INTO public.application_stage_instances "
                "(application_id, workflow_stage_id, status, entered_at, due_at, created_at, created_by) "
                "VALUES (%s, %s, 'in_progress', %s, %s, %s, %s) RETURNING id",
                (app_id, to_stage_id, now, None, now, UUID(subject)),
            )
            new_instance_id = cur.fetchone()["id"]
            print("New stage instance created:", new_instance_id)
            
            # Update application
            cur.execute(
                "UPDATE public.applications "
                "SET current_stage_instance_id = %s, updated_at = %s, updated_by = %s "
                "WHERE id = %s RETURNING id, status, version",
                (new_instance_id, now, UUID(subject), app_id),
            )
            print("Updated app:", cur.fetchone())
            
            # Record stage history
            cur.execute(
                "INSERT INTO public.stage_history "
                "(application_id, from_stage_id, to_stage_id, actor_user_id, reason, event_at, correlation_id, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (app_id, app["current_stage_id"], to_stage_id, UUID(subject), "Test transition", now, None, now),
            )
            print("Recorded stage history.")
