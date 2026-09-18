from enum import Enum
from typing import Any

from pydantic import BaseModel


class AgentAction(str, Enum):
    PLAN = "plan"
    DELEGATE = "delegate"
    COMPLETE = "complete"


class AgentDecision(BaseModel):
    """
    Structured decision made by an agent about its next action.
    """

    action: AgentAction

    target_agent_id: str | None = None

    request: str | None = None

    result: Any | None = None