"""Explicit local prototype identities; real Supabase authentication stays separate.

These development-only tokens never impersonate Supabase JWTs. They exist solely
to preserve the passwordless role cards against the synthetic prototype dataset.
"""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from typing import Annotated

from dotenv import dotenv_values
from fastapi import APIRouter, HTTPException, Request
import jwt
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
SECRET_FILE = ROOT / ".secrets" / "prototype-session.key"
router = APIRouter(tags=["prototype"])

# Stable card keys are intentionally retained from the original login page.
PERSONAS = (
    ("user-institution", "INSTITUTION", "Ananya Rao", "institution"),
    ("user-scrutiny", "SCRUTINY", "Rohan Mehta", "region"),
    ("user-regional", "REGIONAL", "Meera Desai", "region"),
    ("user-coordinator", "EVC_COORDINATOR", "Kabir Shah", "region"),
    ("user-expert-001", "EVC_EXPERT", "Aditi Sharma", "application"),
    ("user-compliance", "COMPLIANCE", "Nisha Sen", "region"),
    ("user-central", "CENTRAL", "Arjun Iyer", "global"),
    ("user-policy", "POLICY", "Tara Menon", "global"),
    ("user-auditor", "AUDITOR", "Dev Sethi", "global"),
    ("user-system", "SYSTEM", "Isha Kapoor", "global"),
)


def enabled(request: Request) -> bool:
    values = dotenv_values(ROOT / ".env")
    flag = os.environ.get("PROTOTYPE_DEMO_ENABLED", values.get("PROTOTYPE_DEMO_ENABLED", "false"))
    return request.app.state.settings.app_env == "development" and str(flag).lower() == "true"


def _secret() -> str:
    try:
        value = SECRET_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        raise HTTPException(status_code=503) from None
    if len(value) < 48:
        raise HTTPException(status_code=503)
    return value


def persona_subject(persona_id: str) -> str:
    from uuid import NAMESPACE_URL, uuid5
    if persona_id not in {p[0] for p in PERSONAS}:
        raise HTTPException(status_code=404)
    return str(uuid5(NAMESPACE_URL, f"aicte-prototype-persona-v1/{persona_id}"))


def verify_prototype_token(request: Request, token: str) -> str | None:
    """Return a subject for our own issuer only; otherwise leave Supabase to verify.

    Unverified decoding is used only to choose the verifier. The accepted subject
    always comes from signature, audience, issuer and expiration verification.
    """
    try:
        untrusted = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return None
    if untrusted.get("iss") != "aicte-prototype":
        return None
    if not enabled(request):
        raise HTTPException(status_code=401)
    try:
        claims = jwt.decode(token, _secret(), algorithms=["HS256"],
                            issuer="aicte-prototype", audience="prototype",
                            options={"require": ["exp", "iat", "sub", "persona"]})
        if claims["persona"] not in {p[0] for p in PERSONAS} or claims["sub"] != persona_subject(claims["persona"]):
            raise ValueError("Subject does not match persona")
        return claims["sub"]
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401) from None


class PersonaSessionRequest(BaseModel):
    persona_id: str = Field(min_length=1, max_length=80)


@router.post("/prototype/session")
def create_session(payload: PersonaSessionRequest, request: Request):
    if not enabled(request):
        raise HTTPException(status_code=404)
    subject = persona_subject(payload.persona_id)
    # Confirm provisioning and dated assignments before issuing a session.
    from .accounts import _read_connection
    with _read_connection(request.app.state.settings.database_url, subject) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT u.id FROM public.users u JOIN public.user_role_assignments a ON a.user_id=u.id "
                "WHERE u.id=%s AND u.identity_subject=u.id::text AND u.status='active' "
                "AND a.status='active' AND a.valid_from<=CURRENT_TIMESTAMP "
                "AND (a.valid_until IS NULL OR a.valid_until>CURRENT_TIMESTAMP) LIMIT 1", (subject,))
            if cursor.fetchone() is None:
                raise HTTPException(status_code=403)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=8)
    token = jwt.encode({"iss": "aicte-prototype", "aud": "prototype", "sub": subject,
                        "persona": payload.persona_id, "iat": now, "exp": expires},
                       _secret(), algorithm="HS256")
    return {"access_token": token, "refresh_token": "prototype",
            "expires_at": int(expires.timestamp() * 1000), "persona_id": payload.persona_id}
