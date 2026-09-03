from persistence import load_workflow
from runtime.event_bus import EventBus
from runtime.runtime_config import RuntimeConfig
from shared_types.completion_status import CompletionStatus
from workflow.graph import app


def resume_workflow(workflow_id):
    state = load_workflow(workflow_id)

    # Reconstruct runtime-only state after restart.
    state["runtime_config"] = RuntimeConfig()
    state["event_bus"] = EventBus()

    # A completed workflow does not need to enter the execution graph again.
    if state.get("completion_status") == CompletionStatus.COMPLETE:
        return state

    # Tell the graph that this is a resumed workflow.
    state["resume"] = True

    return app.invoke(state)
