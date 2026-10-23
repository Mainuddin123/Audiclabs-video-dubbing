
from unittest.mock import Mock, patch

import pytest
import requests

from src.audiclabs_client import AudicLabsClient


@pytest.fixture
def client():
    with patch.dict("os.environ", {"AUDICLABS_API_KEY": "test-key"}):
        return AudicLabsClient()


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "Authentication failed"),
        (403, "Access forbidden"),
        (402, "Payment or API credits required"),
        (413, "Request too large"),
        (422, "Request validation failed"),
        (429, "Rate limit reached"),
        (503, "temporarily unavailable"),
    ],
)
def test_http_errors_have_clear_messages(client, status, expected):
    response = Mock()
    response.ok = False
    response.status_code = status
    response.headers = {"X-Request-Id": "test-request-123"}
    response.text = "test error body"

    with pytest.raises(requests.HTTPError) as exc:
        client._raise_for_status(response, "test operation")

    assert expected in str(exc.value)
    assert "test-request-123" in str(exc.value)


def test_successful_response_does_not_raise(client):
    response = Mock()
    response.ok = True

    client._raise_for_status(response, "test operation")


def test_retry_after_header_is_included_in_error(client):
    response = Mock()
    response.ok = False
    response.status_code = 429
    response.headers = {
        "X-Request-Id": "request-456",
        "Retry-After": "5",
    }
    response.text = "rate limit"

    with pytest.raises(requests.HTTPError) as exc:
        client._raise_for_status(response, "test operation")

    assert "Retry-After: 5" in str(exc.value)
