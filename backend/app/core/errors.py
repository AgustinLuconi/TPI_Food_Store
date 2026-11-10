"""Excepciones de dominio y manejadores globales.

Los services lanzan estas excepciones y nunca `HTTPException`. Un manejador global las traduce
al formato de error estándar: {"detail": "...", "code": "ERROR_CODE", "field": "opcional"}.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class DomainError(Exception):
    status_code = 500
    default_code = "INTERNAL_ERROR"

    def __init__(self, detail: str, code: str | None = None, field: str | None = None):
        super().__init__(detail)
        self.detail = detail
        self.code = code or self.default_code
        self.field = field
        self.headers: dict[str, str] = {}


class NotFoundError(DomainError):
    status_code = 404
    default_code = "NOT_FOUND"


class ConflictError(DomainError):
    status_code = 409
    default_code = "CONFLICT"


class ValidationError(DomainError):
    status_code = 422
    default_code = "VALIDATION_ERROR"


class ForbiddenError(DomainError):
    status_code = 403
    default_code = "FORBIDDEN"


class UnauthorizedError(DomainError):
    """401: sin cookie, token inválido/expirado o credenciales incorrectas."""

    status_code = 401
    default_code = "UNAUTHORIZED"

    def __init__(self, detail: str, code: str | None = None, field: str | None = None):
        super().__init__(detail, code, field)
        self.headers = {"WWW-Authenticate": "Bearer"}


class AccountStateError(DomainError):
    """400: usuario bloqueado o dado de baja (problema de la cuenta, no de las credenciales)."""

    status_code = 400
    default_code = "ACCOUNT_DISABLED"


class TooManyRequestsError(DomainError):
    status_code = 429
    default_code = "TOO_MANY_REQUESTS"

    def __init__(self, detail: str, retry_after: int, code: str | None = None):
        super().__init__(detail, code)
        self.headers = {"Retry-After": str(max(1, retry_after))}


def _body(detail: str, code: str, field: str | None = None) -> dict[str, str]:
    body = {"detail": detail, "code": code}
    if field:
        body["field"] = field
    return body


async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_body(exc.detail, exc.code, exc.field),
        headers=exc.headers or None,
    )


async def _request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = [str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path", "header")]
    field = ".".join(loc) or None
    message = str(first.get("msg", "Datos inválidos")).removeprefix("Value error, ")
    return JSONResponse(status_code=422, content=_body(message, "VALIDATION_ERROR", field))


async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Error"
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=_body(detail, code),
        headers=getattr(exc, "headers", None),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _request_validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
