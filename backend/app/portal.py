"""One authoritative projection for all portal registers and analytics."""
from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response
from .accounts import _user
from .auth import get_verified_subject
from .portal_snapshot import snapshot
from .transactions import write_transaction

router = APIRouter(tags=["portal"])

@router.get("/portal/snapshot")
def portal_snapshot(request: Request, response: Response, subject: Annotated[str, Depends(get_verified_subject)]):
    _user(request, subject)
    response.headers["Cache-Control"] = "no-store"
    with write_transaction(request.app.state.settings.database_write_url, subject) as connection:
        return snapshot(connection, subject)
