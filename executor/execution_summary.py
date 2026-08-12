from dataclasses import dataclass


@dataclass
class ExecutionSummary:
    total_steps: int
    succeeded: int
    failed: int
    skipped: int
    duration: float