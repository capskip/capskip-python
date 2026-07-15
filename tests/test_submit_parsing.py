"""Unit tests for in.php submit-response parsing (_parse_submit_response)."""

import pytest

from capskip.solver import _parse_submit_response
from capskip.exceptions import ApiException


def test_ok_form():
    assert _parse_submit_response('OK|12345') == '12345'


def test_ok_form_is_stripped():
    assert _parse_submit_response('OK|12345\n') == '12345'


def test_json_form():
    # CapSkip returns this shape when the submit carried json=1.
    assert _parse_submit_response('{"status":1,"request":"12345"}') == '12345'


def test_unrecognized_response_raises():
    with pytest.raises(ApiException):
        _parse_submit_response('SOMETHING_UNEXPECTED')


def test_json_without_success_status_raises():
    with pytest.raises(ApiException):
        _parse_submit_response('{"status":0,"request":"ERROR"}')
