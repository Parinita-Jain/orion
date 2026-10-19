
from google.genai.errors import APIError


def is_quota_or_rate_limit_error(error: BaseException) -> bool:
    """Return True only for Google GenAI HTTP 429 errors."""
    if not isinstance(error, APIError):
        return False

    code = getattr(error, "code", None)
    if code is None:
        code = getattr(error, "status", None)

    return code == 429
