from dataclasses import dataclass, field
from runtime.approval_request import ApprovalRequest

@dataclass
class PlanStep:
    """
    One executable step in a plan.
    """

    id: int
    tool: str
    tool_input: str
    depends_on: list[int] = field(default_factory=list)
    output: str | None = None
    
    timeout: float | None = None
    approval: ApprovalRequest | None = None

    condition: str | None = None

    replaces: int | None = None

    
@dataclass
class Plan:
    """
    Complete execution plan.
    """

    steps: list[PlanStep]