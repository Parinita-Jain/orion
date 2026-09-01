from persistence import load_workflow
from runtime.event_bus import EventBus
from runtime.runtime_config import RuntimeConfig
from workflow.graph import app

def resume_workflow(workflow_id):
    state = load_workflow(workflow_id)

    state["runtime_config"] = RuntimeConfig()
    state["event_bus"] = EventBus()
    state["resume"] = True

    return app.invoke(state)