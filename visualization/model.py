from dataclasses import dataclass, field
from enum import Enum

from shared_types.completion_status import CompletionStatus
from shared_types.step_status import StepStatus


class EdgeType(str, Enum):
    DEPENDENCY = "dependency"
    REPLACEMENT = "replacement"


@dataclass
class WorkflowNode:
    id: int
    tool: str
    status: StepStatus | None = None
    retries: int = 0
    duration: float = 0.0
    error: str | None = None
    condition: str | None = None
    approval_required: bool = False
    replaces: int | None = None


@dataclass
class WorkflowEdge:
    source: int
    target: int
    type: EdgeType


@dataclass
class WorkflowGraph:
    workflow_id: str
    completion_status: CompletionStatus | None = None
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)
