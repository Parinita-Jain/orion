from models.plan import PlanStep

from dataclasses import asdict,is_dataclass

def serialize_step(step):
    if is_dataclass(step):
        return asdict(step)

    if hasattr(step, "model_dump"):
        return step.model_dump()

    raise TypeError(
        f"Unsupported step type: {type(step)}"
    )

def serialize_tool_result(result):

    return {
        "output": result.get("output"),
        "success": result.get("success"),
        "status": result.get("status"),
        "error": result.get("error"),
        "failure_reason": result.get("failure_reason"),
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
        }
    }

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
    }