from __future__ import annotations

from dataclasses import dataclass


class AppError(Exception):
    """Base class for app-specific exceptions."""

    retryable: bool = False
    error_code: str = "app_error"

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        if error_code:
            self.error_code = error_code


class RetryableAppError(AppError):
    """Base exception for transient failures that can be retried."""

    retryable: bool = True
    error_code: str = "retryable_error"


class NonRetryableAppError(AppError):
    """Base exception for permanent failures that should not be retried."""

    retryable: bool = False
    error_code: str = "non_retryable_error"


@dataclass(frozen=True)
class ErrorClassification:
    retryable: bool
    error_type: str
    error_code: str


def classify_exception(exc: Exception) -> ErrorClassification:
    """Classify unknown exceptions by retry behavior for telemetry and response shaping."""
    if isinstance(exc, AppError):
        return ErrorClassification(
            retryable=exc.retryable,
            error_type=exc.__class__.__name__,
            error_code=exc.error_code,
        )

    retryable_names = {
        "TimeoutException",
        "ReadTimeout",
        "ConnectTimeout",
        "PoolTimeout",
        "OperationalError",
        "InterfaceError",
        "ServerDisconnectedError",
    }

    if isinstance(exc, (TimeoutError, ConnectionError)) or exc.__class__.__name__ in retryable_names:
        return ErrorClassification(
            retryable=True,
            error_type=exc.__class__.__name__,
            error_code="transient_dependency_failure",
        )

    return ErrorClassification(
        retryable=False,
        error_type=exc.__class__.__name__,
        error_code="internal_error",
    )
