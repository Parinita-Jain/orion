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

def serialize_state(state):

    return {
        "workflow_id": state.get("workflow_id"),
        "iteration": state.get("iteration", 0),
        "steps": [
            serialize_step(step)
            for step in state.get("steps", [])
        ],
    }

def deserialize_state(data):

    return {
        "workflow_id": data["workflow_id"],
        "iteration": data["iteration"],
        "steps": [
            PlanStep(**step)
            for step in data.get("steps", [])
        ],
    }