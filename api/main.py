import json
from uuid import uuid4

import tools  # noqa: F401 — registers Orion tools

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from workflow.graph import app as workflow_app
from runtime.event_bus import EventBus
from runtime.runtime_config import RuntimeConfig
from runtime.logging_listener import LoggingEventListener
from runtime.metrics_listener import MetricsListener
from runtime.audit_listener import AuditListener
from runtime.stream import stream_workflow


app = FastAPI(
    title="Orion API",
    description="REST API for the Orion agentic AI workflow.",
    version="1.0.0",
)


class WorkflowRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10000)


class WorkflowResponse(BaseModel):
    workflow_id: str
    answer: str


def create_workflow_state(question: str) -> tuple[str, dict]:
    """Create an independent workflow state and its monitoring listeners."""
    workflow_id = str(uuid4())

    bus = EventBus()
    bus.subscribe(LoggingEventListener())
    bus.subscribe(MetricsListener())
    bus.subscribe(AuditListener())

    state = {
        "workflow_id": workflow_id,
        "messages": [HumanMessage(content=question)],
        "steps": [],
        "tool_results": {},
        "execution_records": [],
        "context": {},
        "output": {},
        "documents": [],
        "tool_input": "",
        "done": False,
        "iteration": 0,
        "errors": [],
        "error": None,
        "runtime_config": RuntimeConfig(),
        "event_bus": bus,
        "agent_tasks": {},
        "agent_messages": [],
        "current_agent_task_id": None,
        "agent_next_node": None,
    }

    return workflow_id, state


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/workflow", response_model=WorkflowResponse)
def execute_workflow(request: WorkflowRequest):
    workflow_id, state = create_workflow_state(request.question)

    try:
        result = workflow_app.invoke(state)
        
        if result.get("error") is not None:
            raise HTTPException(
                status_code=500,
                detail="Workflow execution failed.",
            )

        messages = result.get("messages", [])

        if not messages:
            raise RuntimeError("Workflow returned no messages.")

        answer = messages[-1].content

        if not isinstance(answer, str):
            answer = str(answer)

        return WorkflowResponse(
            workflow_id=workflow_id,
            answer=answer,
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Workflow execution failed.",
        ) from exc


@app.post("/workflow/stream")
def stream_workflow_endpoint(request: WorkflowRequest):
    _, state = create_workflow_state(request.question)

    # WorkflowStream subscribes its queue to this same bus.
    stream = stream_workflow(state, event_bus=state["event_bus"])

    def generate_events():
        for event in stream:
            event_name = event.type.value
            event_data = {
                "type": event_name,
                "timestamp": event.timestamp,
                "step_id": event.step_id,
                "tool": event.tool,
                "payload": event.payload,
                "agent_task_id": event.agent_task_id,
                "agent_id": event.agent_id,
            }

            yield (
                f"event: {event_name}\n"
                f"data: {json.dumps(event_data, default=str)}\n\n"
            )

        if stream.error is not None:
            yield (
                "event: error\n"
                'data: {"detail":"Workflow execution failed."}\n\n'
            )

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
