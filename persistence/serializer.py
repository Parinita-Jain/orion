def serialize_state(state):
    return {
        "workflow_id": state.get("workflow_id"),
        "iteration": state.get("iteration", 0),
    }

def deserialize_state(data):

    return {
        "workflow_id": data["workflow_id"],
        "iteration": data["iteration"],
    }
    