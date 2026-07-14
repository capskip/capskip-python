"""CapSkip Python SDK — local captcha solver client."""

from .api import ApiClient
from .async_api import AsyncApiClient
from .async_solver import AsyncCapSkip
from .exceptions import (
    ApiException,
    CapSkipError,
    NetworkException,
    SolverExceptions,
    TimeoutException,
    ValidationException,
)
from .solver import CapSkip

__all__ = [
    'CapSkip',
    'AsyncCapSkip',
    'ApiClient',
    'AsyncApiClient',
    'CapSkipError',
    'SolverExceptions',
    'ValidationException',
    'NetworkException',
    'ApiException',
    'TimeoutException',
]

__version__ = '1.0.1'
