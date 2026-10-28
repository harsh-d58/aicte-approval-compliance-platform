"""Validate configured OIDC bearer tokens; never trust client-supplied roles or scopes."""

from functools import lru_cache
import json
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from fastapi import HTTPException, Request
import jwt
from jwt import PyJWKClient


@lru_cache(maxsize=4)
def _jwk_client(issuer: str) -> PyJWKClient:
    parsed_issuer = urlsplit(issuer)
    if parsed_issuer.scheme != "https" or not parsed_issuer.hostname:
        raise ValueError("Identity issuer must use HTTPS")
    discovery_url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    with urlopen(discovery_url, timeout=3) as response:
        discovery = json.load(response)
    jwks_uri = discovery.get("jwks_uri", "")
    parsed_jwks = urlsplit(jwks_uri)
    if (
        discovery.get("issuer") != issuer
        or parsed_jwks.scheme != "https"
        or parsed_jwks.hostname != parsed_issuer.hostname
    ):
        raise ValueError("Invalid identity-provider discovery metadata")
    return PyJWKClient(jwks_uri, timeout=3, lifespan=300)


def get_verified_subject(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token or len(token) > 16384:
        raise HTTPException(status_code=401)

    settings = request.app.state.settings
    if not settings.identity_issuer_url or not settings.identity_audience:
        raise HTTPException(status_code=503)
    try:
        signing_key = _jwk_client(settings.identity_issuer_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.identity_audience,
            issuer=settings.identity_issuer_url,
            options={"require": ["exp", "iss", "aud", "sub"]},
            leeway=30,
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401) from None
    except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=503) from None
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise HTTPException(status_code=401)
    return subject
