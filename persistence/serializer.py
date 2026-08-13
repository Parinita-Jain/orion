from models.plan import PlanStep

from dataclasses import asdict,is_dataclass

from shared_types.completion_status import CompletionStatus

from models.execution_record import ExecutionRecord

from langchain_core.messages import HumanMessage, AIMessage


def serialize_step(step):
    if is_dataclass(step):
        return asdict(step)

    if hasattr(step, "model_dump"):
        return step.model_dump()

    raise TypeError(
        f"Unsupported step type: {type(step)}"
    )

def serialize_execution_record(record):
    return asdict(record)

def serialize_tool_result(result):

    return {
        "output": result.get("output"),
        "success": result.get("success"),
        "status": result.get("status"),
        "error": result.get("error"),
        "failure_reason": result.get("failure_reason"),
    }

def serialize_message(message):
    return {
        "type": message.type,
        "content": message.content,
        "id": message.id,
    }

def serialize_state(state):

    return {
        "workflow_id": state.get("workflow_id"),
        "iteration": state.get("iteration", 0),
        "steps": [
            serialize_step(step)
            for step in state.get("steps", [])
        ],
        "tool_results": {
            int(step_id): serialize_tool_result(result)
            for step_id, result in state.get(
                "tool_results",
                {},
            ).items()
        },
        "completion_status": (
            state["completion_status"].value
            if state.get("completion_status") is not None
            else None
        ),
        "execution_records": [
            serialize_execution_record(record)
            for record in state.get("execution_records", [])
        ],
        "messages": [
            serialize_message(message)
            for message in state.get("messages", [])
        ],
        "context": state.get("context", {}),
    }

def deserialize_message(message):
    if message["type"] == "human":
        return HumanMessage(content=message["content"])

    if message["type"] == "ai":
        return AIMessage(content=message["content"])

    raise ValueError(
        f"Unsupported message type: {message['type']}"
    )

def deserialize_state(data):

    return {
        "workflow_id": data["workflow_id"],
        "iteration": data["iteration"],
        "steps": [
            PlanStep(**step)
            for step in data.get("steps", [])
        ],
        "tool_results": {
            int(step_id): result
            for step_id, result in data.get(
                "tool_results",
                {},
            ).items()
        },
        "completion_status": (
            CompletionStatus(data["completion_status"])
            if data.get("completion_status") is not None
            else None
        ),
        "execution_records": [
            ExecutionRecord(**record)
            for record in data.get("execution_records", [])
        ],
        "messages": [
            deserialize_message(message)
            for message in data.get("messages", [])
        ],
        "context": data.get("context", {}),
    }