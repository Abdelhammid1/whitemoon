"""HTTP-aware error types used across blueprints.

Each error carries a stable string code (so UIs can i18n) plus a status.
Flask error handlers convert them to JSON responses.
"""

from __future__ import annotations


class ApiError(Exception):
    status: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status


class BadRequest(ApiError):
    status = 400
    code = "bad_request"


class Unauthorized(ApiError):
    status = 401
    code = "unauthorized"


class Forbidden(ApiError):
    status = 403
    code = "forbidden"


class NotFound(ApiError):
    status = 404
    code = "not_found"


class Conflict(ApiError):
    status = 409
    code = "conflict"


class UnprocessableEntity(ApiError):
    status = 422
    code = "unprocessable_entity"


class TooManyRequests(ApiError):
    status = 429
    code = "too_many_requests"
