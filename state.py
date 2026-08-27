from typing import Annotated, Sequence, Any
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from schemas import PlanStep
from errors import OrionError

from models.execution_record import ExecutionRecord
from config import logger

from shared_types.completion_status import CompletionStatus

from runtime.runtime_config import RuntimeConfig
from runtime.event_bus import EventBus

class AgentState(TypedDict):

    messages: Annotated[
        Sequence[BaseMessage],
        add_messages
    ]

    steps: list[PlanStep]

    tool_input: str

    documents: list[Any]

    output: dict[str, Any]

    context: dict[str, Any]

    tool_results: dict[int, dict]

    done: bool

    execution_records: list[ExecutionRecord]

    # ---------- NEW ----------

    error: OrionError | None

    errors: list[str]

    iteration: int

    workflow_id: str

    completion_status: CompletionStatus

    runtime_config: RuntimeConfig

    event_bus: EventBus