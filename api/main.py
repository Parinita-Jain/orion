from uuid import uuid4

import tools  # noqa: F401 — registers Orion tools

from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from workflow.graph import app as workflow_app
from runtime.event_bus import EventBus
from runtime.runtime_config import RuntimeConfig
from runtime.logging_listener import LoggingEventListener
from runtime.metrics_listener import MetricsListener
from runtime.audit_listener import AuditListener


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


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/workflow", response_model=WorkflowResponse)
def execute_workflow(request: WorkflowRequest):

    workflow_id = str(uuid4())

    bus = EventBus()
    metrics = MetricsListener()
    audit = AuditListener()

    bus.subscribe(LoggingEventListener())
    bus.subscribe(metrics)
    bus.subscribe(audit)

    state = {
        "workflow_id": workflow_id,
        "messages": [HumanMessage(content=request.question)],
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

    try:
        result = workflow_app.invoke(state)

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

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Workflow execution failed.",
        ) from exc
