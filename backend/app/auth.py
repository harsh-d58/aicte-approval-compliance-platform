"""Verify Supabase Auth access tokens; database assignments grant application access."""

from functools import lru_cache
from urllib.error import URLError
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException, Request
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKSetError


ALGORITHMS = ("ES256", "RS256")
AUDIENCE = "authenticated"


def _issuer(project_url: str) -> str:
    parsed = urlsplit(project_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("SUPABASE_URL must be an HTTPS project base URL")
    return project_url.rstrip("/") + "/auth/v1"


@lru_cache(maxsize=4)
def _jwks_client(project_url: str) -> PyJWKClient:
    return PyJWKClient(_issuer(project_url) + "/.well-known/jwks.json", timeout=8, lifespan=300)


def get_verified_subject(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token or len(token) > 16384:
        raise HTTPException(status_code=401)

    project_url = request.app.state.settings.supabase_url
    if not project_url:
        raise HTTPException(status_code=503)
    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if algorithm not in ALGORITHMS or not isinstance(header.get("kid"), str) or not header["kid"]:
            raise HTTPException(status_code=401)
        signing_key = _jwks_client(project_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience=AUDIENCE,
            issuer=_issuer(project_url),
            options={"require": ["exp", "iat", "iss", "aud", "sub", "role", "session_id"]},
            leeway=30,
        )
    except HTTPException:
        raise
    except (PyJWKClientConnectionError, PyJWKSetError):
        raise HTTPException(status_code=503) from None
    except jwt.PyJWTError:
        raise HTTPException(status_code=401) from None
    except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=503) from None

    if claims.get("role") != AUDIENCE or claims.get("is_anonymous") is not False:
        raise HTTPException(status_code=401)
    try:
        subject = str(UUID(claims["sub"]))
        UUID(claims["session_id"])
    except (ValueError, TypeError, KeyError, AttributeError):
        raise HTTPException(status_code=401) from None
    return subject
