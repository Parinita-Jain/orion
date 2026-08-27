import time
from config import logger
from runtime.retry_error import RetryError
def execute_with_retry(
    func,
    *args,
    max_retries: int = 0,
    tool_name: str,
    **kwargs,
):
    """
    
    Execute a callable with exponential backoff.

    Returns:
        The callable's return value.

    Raises:
        The last exception encountered if all retry attempts fail.
    """

    last_exception = None

    for attempt in range(max_retries + 1):

        try:
            return func(*args, **kwargs), attempt

        except Exception as e:

            last_exception = e

            logger.warning(
                "Attempt %d/%d failed for tool '%s': %s",
                attempt + 1,
                max_retries + 1,
                tool_name,
                e,
            )

            if attempt < max_retries:

                wait_time = 2 ** attempt

                logger.info(
                    "Retrying tool '%s' in %d second(s)",
                    tool_name,
                    wait_time,
                )

                time.sleep(wait_time)

    if last_exception is not None:
        raise RetryError(
            retries=max_retries,
            original_exception=last_exception,
        )

    raise RuntimeError("execute_with_retry failed without capturing an exception.")