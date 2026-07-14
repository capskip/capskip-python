"""Unit tests for res.php response parsing (_parse_poll_response)."""

import pytest

from capskip.solver import _parse_poll_response
from capskip.exceptions import ApiException, NetworkException


@pytest.mark.parametrize('body', ['', '   ', '\n', None])
@pytest.mark.parametrize('json_mode', [0, 1])
def test_empty_body_is_retryable(body, json_mode):
    # CapSkip returns an empty body before a result is available; it must be
    # signalled as "not ready" (NetworkException), never a fatal ApiException.
    with pytest.raises(NetworkException):
        _parse_poll_response(body, json_mode=json_mode)


def test_not_ready_marker():
    with pytest.raises(NetworkException):
        _parse_poll_response('CAPCHA_NOT_READY')


def test_ok_token():
    assert _parse_poll_response('OK|thetoken') == 'thetoken'


def test_ok_token_is_stripped():
    assert _parse_poll_response('OK|thetoken\n') == 'thetoken'


def test_unrecognized_response_raises():
    with pytest.raises(ApiException):
        _parse_poll_response('SOMETHING_UNEXPECTED')


def test_json_ready():
    data = _parse_poll_response('{"status":1,"request":"tok"}', json_mode=1)
    assert data['request'] == 'tok'


def test_json_not_ready_is_retryable():
    with pytest.raises(NetworkException):
        _parse_poll_response('{"status":0,"request":"CAPCHA_NOT_READY"}', json_mode=1)
