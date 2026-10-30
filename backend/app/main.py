"""FastAPI contract foundation; business routes wait for verified schema and identity."""

from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from .accounts import router as accounts_router
from .applications import router as applications_router
from .compliance import router as compliance_router
from .dashboards import router as dashboards_router
from .database import database_is_available
from .decisions import router as decisions_router
from .deficiencies import router as deficiencies_router
from .documents import router as documents_router
from .evc import router as evc_router
from .institutions import router as institutions_router
from .meeting_records import router as meeting_records_router
from .notifications import router as notifications_router
from .ocr import router as ocr_router
from .records import router as records_router
from .reports import router as reports_router
from .settings import Settings
from .users import router as users_router
from .workflows import router as workflows_router
from .authorization import authorize_request
from .portal import router as portal_router
from .portal_files import router as portal_files_router
from .portal_commands import router as portal_commands_router
from .prototype import router as prototype_router


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid4()))


def _error(request: Request, status: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {
            "code": code,
            "message": message,
            "details": details or {},
            "correlation_id": _correlation_id(request),
        }},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.load()
    app = FastAPI(
        title="AICTE Approval and Compliance API",
        version="0.1.0",
        docs_url="/docs" if config.app_env == "development" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if config.app_env == "development" else None,
        dependencies=[Depends(authorize_request)],
    )
    app.state.settings = config
    allowed_origins = [config.frontend_origin] if config.frontend_origin else []
    if config.app_env == "development":
        allowed_origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "Idempotency-Key", "If-Match"],
        expose_headers=["X-Correlation-ID"],
    )
    app.include_router(accounts_router, prefix=config.api_prefix)
    app.include_router(records_router, prefix=config.api_prefix)
    app.include_router(users_router, prefix=config.api_prefix)
    app.include_router(institutions_router, prefix=config.api_prefix)
    app.include_router(workflows_router, prefix=config.api_prefix)
    app.include_router(applications_router, prefix=config.api_prefix)
    app.include_router(deficiencies_router, prefix=config.api_prefix)
    app.include_router(decisions_router, prefix=config.api_prefix)
    app.include_router(documents_router, prefix=config.api_prefix)
    app.include_router(ocr_router, prefix=config.api_prefix)
    app.include_router(evc_router, prefix=config.api_prefix)
    app.include_router(meeting_records_router, prefix=config.api_prefix)
    app.include_router(compliance_router, prefix=config.api_prefix)
    app.include_router(notifications_router, prefix=config.api_prefix)
    app.include_router(dashboards_router, prefix=config.api_prefix)
    app.include_router(reports_router, prefix=config.api_prefix)
    app.include_router(portal_router, prefix=config.api_prefix)
    app.include_router(portal_files_router, prefix=config.api_prefix)
    app.include_router(portal_commands_router, prefix=config.api_prefix)
    app.include_router(prototype_router, prefix=config.api_prefix)

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        proposed = request.headers.get("X-Correlation-ID", "")
        try:
            request.state.correlation_id = str(UUID(proposed))
        except ValueError:
            request.state.correlation_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception:
            import traceback
            traceback.print_exc()
            response = _error(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        standard = {
            401: ("UNAUTHENTICATED", "Authentication is required."),
            400: ("INVALID_REQUEST", "Request is invalid."),
            403: ("FORBIDDEN", "Access is not permitted."),
            404: ("NOT_FOUND", "Resource not found."),
            405: ("METHOD_NOT_ALLOWED", "Method not allowed."),
            409: ("CONFLICT", "The requested action conflicts with current state."),
            412: ("PRECONDITION_FAILED", "The record changed; reload before trying again."),
            503: ("DEPENDENCY_UNAVAILABLE", "Backend dependencies are not ready."),
        }
        if error.status_code in standard:
            code, message = standard[error.status_code]
            if error.status_code == 409 and error.detail in (
                'Complete the EVC visit before approving its report',
                'Resolve all deficiency items before approving the EVC report',
                'Submit the current draft for review before approval',
                'Record source content changed; generate a new version',
                'Only an approved application can be closed',
                'Close every verified approval condition before closing the application',
                'This application already has a final decision',
                'Complete the configured review route before recording a decision',
                'Resolve every deficiency item before recording a decision',
                'Complete the EVC visit and approve its report before recording a decision',
                'Reopen the application before reopening this condition',
                'Only a condition with accepted evidence can be closed',
            ):
                message = error.detail
            return _error(request, error.status_code, code, message)
        return _error(request, error.status_code, "HTTP_ERROR", str(error.detail) if getattr(error, "detail", None) else "Request could not be completed.")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        # Exclude submitted values and raw validator messages, which may contain secrets.
        fields = [
            {"location": [str(part) for part in issue["loc"]], "type": issue["type"]}
            for issue in error.errors()
        ]
        return _error(request, 422, "INVALID_REQUEST", "Request validation failed.", {"fields": fields})

    @app.get("/health", include_in_schema=False)
    def liveness():
        return {"status": "alive"}

    @app.get("/ready", include_in_schema=False)
    def readiness(request: Request):
        if not config.supabase_url or not database_is_available(config.database_url):
            return _error(request, 503, "DEPENDENCY_UNAVAILABLE", "Backend dependencies are not ready.")
        return {"status": "ready"}

    return app


app = create_app()
