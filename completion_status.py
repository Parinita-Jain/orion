from enum import Enum


class CompletionStatus(str, Enum):

    COMPLETE = "complete"

    CONTINUE = "continue"

    REPLAN = "replan"

    FAILED = "failed"