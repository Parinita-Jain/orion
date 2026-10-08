from typing import Literal
from pydantic import BaseModel
from typing import Optional

class ApprovalConfig(BaseModel):

    required: bool = False

    reason: str | None = None

    role: str | None = None

class PlannerStep(BaseModel):

    id: int

    tool: str

    tool_input: str

    depends_on: list[int]

    output: Optional[str] = None

    approval: ApprovalConfig | None = None

    condition: str | None = None

    replaces: int | None = None

class PlannerOutput(BaseModel):

    steps: list[PlannerStep]

class ReplannerOutput(BaseModel):

    done: bool

    steps: list[PlannerStep]