from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agents.task import AgentTaskStatus
from shared_types.completion_status import CompletionStatus
from shared_types.step_status import StepStatus


class EdgeType(str, Enum):
    DEPENDENCY = "dependency"
    REPLACEMENT = "replacement"


class AgentEdgeType(str, Enum):
    DELEGATION = "delegation"
    OWNERSHIP = "ownership"


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
    agent_task_id: str | None = None
    agent_id: str | None = None


@dataclass
class AgentTaskNode:
    task_id: str
    parent_task_id: str | None
    agent_id: str
    request: str
    status: AgentTaskStatus
    result: Any | None = None
    error: str | None = None
    message_count: int = 0


@dataclass
class WorkflowEdge:
    source: int
    target: int
    type: EdgeType


@dataclass
class AgentEdge:
    source: str
    target: str
    type: AgentEdgeType


@dataclass
class WorkflowGraph:
    workflow_id: str
    completion_status: CompletionStatus | None = None
    agent_tasks: list[AgentTaskNode] = field(default_factory=list)
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)
    agent_edges: list[AgentEdge] = field(default_factory=list)