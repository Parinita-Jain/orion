from google.genai.errors import APIError


def is_quota_or_rate_limit_error(error: BaseException) -> bool:
    """Return True only when an exception chain contains an HTTP 429 error."""
    current = error
    visited: set[int] = set()

    while current is not None and id(current) not in visited:
        visited.add(id(current))

        if isinstance(current, APIError):
            code = getattr(current, "code", None)
            if code is None:
                code = getattr(current, "status", None)

            if code == 429:
                return True

        current = current.__cause__ or current.__context__

    return False
