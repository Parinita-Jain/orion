from enum import Enum


class FailureReason(str, Enum):

    EXCEPTION = "exception"

    TIMEOUT = "timeout"

    CANCELLED = "cancelled"

    VALIDATION = "validation"

    APPROVAL_REJECTED = "approval_rejected"

    UNKNOWN_TOOL = "unknown_tool"

    PLANNER_ERROR = "planner_error"