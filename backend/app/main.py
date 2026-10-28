"""FastAPI contract foundation; business routes wait for verified schema and identity."""

from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .database import database_is_available
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
        if error.status_code == 404:
            return _error(request, 404, "NOT_FOUND", "Resource not found.")
        if error.status_code == 405:
            return _error(request, 405, "METHOD_NOT_ALLOWED", "Method not allowed.")
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
        if not config.identity_issuer_url or not config.identity_audience or not database_is_available(config.database_url):
            return _error(request, 503, "DEPENDENCY_UNAVAILABLE", "Backend dependencies are not ready.")
        return {"status": "ready"}

    return app


app = create_app()
