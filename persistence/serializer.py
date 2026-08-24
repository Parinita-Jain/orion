from models.plan import PlanStep

from dataclasses import asdict,is_dataclass

from shared_types.completion_status import CompletionStatus

from models.execution_record import ExecutionRecord

from langchain_core.messages import HumanMessage, AIMessage

from runtime.approval_request import ApprovalRequest

from errors import OrionError, ErrorType

from shared_types.step_status import StepStatus

def serialize_error(error):

    if error is None:
        return None

    return {
        "error_type": error.error_type.value,
        "message": error.message,
        "recoverable": error.recoverable,
        "source": error.source,
    }


def deserialize_error(data):

    if data is None:
        return None

    return OrionError(
        error_type=ErrorType(data["error_type"]),
        message=data["message"],
        recoverable=data["recoverable"],
        source=data.get("source", "unknown"),
    )


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
        "messages": [
            serialize_message(message)
            for message in result.get("messages", [])
        ],
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

def deserialize_message(message):
    if message["type"] == "human":
        return HumanMessage(content=message["content"])

    if message["type"] == "ai":
        return AIMessage(content=message["content"])

    raise ValueError(
        f"Unsupported message type: {message['type']}"
    )

def serialize_state(state):

    return {
        "workflow_id": state.get("workflow_id"),
        "iteration": state.get("iteration", 0),
        "done": state.get("done", False),
        "error": serialize_error(
            state.get("error")
        ),
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
        "output": state.get("output", {}),
    }

def deserialize_state(data):

    steps = []

    for step in data.get("steps", []):

        approval_data = step.get("approval")

        if approval_data is not None:
            step["approval"] = ApprovalRequest(
                **approval_data
            )

        steps.append(
            PlanStep(**step)
        )

    return {
        "workflow_id": data["workflow_id"],
        "iteration": data["iteration"],
        "done": data.get("done", False),
        "error": deserialize_error(
            data.get("error")
        ),
        "steps": steps,
        # keep your other existing restored fields here

        "tool_results": {
            int(step_id): {
                **result,
                "status": (
                    StepStatus(result["status"])
                    if result.get("status") is not None
                    else None
                ),
                "messages": [
                    deserialize_message(message)
                    for message in result.get("messages", [])
                ],
            }
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
        "output": data.get("output", {}),
    }
