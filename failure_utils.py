from shared_types.failure_reason import FailureReason


RECOVERABLE_FAILURES = {
    FailureReason.TIMEOUT,
    FailureReason.CANCELLED,
}


def is_recoverable_failure(
    reason: FailureReason | None,
) -> bool:

    return reason in RECOVERABLE_FAILURES