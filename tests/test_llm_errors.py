
import pytest
from google.genai.errors import APIError

from runtime.llm_errors import is_quota_or_rate_limit_error


@pytest.mark.parametrize("code", [429])
def test_quota_or_rate_limit_error_is_detected(code):
    error = APIError(code, {"message": "Resource exhausted"})

    assert is_quota_or_rate_limit_error(error) is True


@pytest.mark.parametrize("code", [400, 401, 403, 404, 500, 503])
def test_other_http_errors_are_not_classified_as_quota(code):
    error = APIError(code, {"message": "Request failed"})

    assert is_quota_or_rate_limit_error(error) is False


def test_non_google_exception_is_not_classified_as_quota():
    error = RuntimeError("429 quota exhausted")

    assert is_quota_or_rate_limit_error(error) is False
