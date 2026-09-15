from dataclasses import dataclass


@dataclass
class ExecutionRecord:
    """
    Metadata for one executed step.
    """

    step_id: int

    tool: str

    success: bool

    retries: int

    start_time: float

    end_time: float

    duration: float

    error: str | None = None

    agent_task_id: str | None = None