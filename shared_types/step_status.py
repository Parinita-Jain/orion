from enum import Enum


class StepStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    SUPERSEDED = "superseded"