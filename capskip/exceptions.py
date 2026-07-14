class CapSkipError(Exception):
    """Base exception for all CapSkip SDK errors."""


SolverExceptions = CapSkipError


class ValidationException(CapSkipError):
    """Invalid or unsupported parameters."""


class NetworkException(CapSkipError):
    """Connection failure or captcha not ready."""


class ApiException(CapSkipError):
    """CapSkip API returned an error."""


class TimeoutException(CapSkipError):
    """Polling exceeded the configured timeout."""
