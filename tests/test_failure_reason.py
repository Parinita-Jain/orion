from enums.failure_reason import FailureReason


def test_failure_reason_values():

    assert FailureReason.TIMEOUT.value == "timeout"
    assert FailureReason.EXCEPTION.value == "exception"