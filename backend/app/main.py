"""FastAPI contract foundation; business routes wait for verified schema and identity."""

from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .accounts import router as accounts_router
from .database import database_is_available
from .records import router as records_router
from .settings import Settings


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
    )
    app.state.settings = config
    app.include_router(accounts_router, prefix=config.api_prefix)
    app.include_router(records_router, prefix=config.api_prefix)

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
            503: ("DEPENDENCY_UNAVAILABLE", "Backend dependencies are not ready."),
        }
        if error.status_code in standard:
            code, message = standard[error.status_code]
            return _error(request, error.status_code, code, message)
        return _error(request, error.status_code, "HTTP_ERROR", "Request could not be completed.")

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
