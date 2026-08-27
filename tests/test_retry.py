import pytest
from unittest.mock import patch, call

from runtime.retry import execute_with_retry
from runtime.retry_error import RetryError

def test_execute_success_first_attempt():

    def succeed():
        return "success"

    with patch("runtime.retry.time.sleep") as mock_sleep:

        result, retries = execute_with_retry(
            succeed,
            tool_name="dummy",
            max_retries=2,
        )

        assert result == "success"
        assert retries == 0
        mock_sleep.assert_not_called()


def test_execute_success_after_retry():

    attempts = 0

    def flaky():

        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise ValueError("Temporary failure")

        return "success"

    with patch("runtime.retry.time.sleep") as mock_sleep:

        result, retries = execute_with_retry(
            flaky,
            tool_name="dummy",
            max_retries=2,
        )

        assert result == "success"
        assert retries == 1
        assert attempts == 2
        mock_sleep.assert_called_once_with(1)


def test_execute_failure_after_max_retries():

    def always_fail():
        raise ValueError("Permanent failure")

    with patch("runtime.retry.time.sleep"):

        with pytest.raises(RetryError) as exc:

            execute_with_retry(
                always_fail,
                tool_name="dummy",
                max_retries=3,
            )

        assert isinstance(
            exc.value.original_exception,
            ValueError,
        )

        assert exc.value.retries == 3


def test_exponential_backoff():

    def always_fail():
        raise RuntimeError("Boom")

    with patch("runtime.retry.time.sleep") as mock_sleep:

        with pytest.raises(RetryError) as exc:

            execute_with_retry(
                always_fail,
                tool_name="dummy",
                max_retries=3,
            )

        assert isinstance(
            exc.value.original_exception,
            RuntimeError,
        )

        assert exc.value.retries == 3

        mock_sleep.assert_has_calls(
            [
                call(1),
                call(2),
                call(4),
            ]
        )