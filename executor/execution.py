from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionRecord:

    step_id: int

    tool: str

    success: bool

    retries: int

    start_time: float

    end_time: float

    duration: float

    error: Optional[str] = None