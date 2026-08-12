import tools
import uuid
from workflow.graph import app
from langchain_core.messages import HumanMessage
from runtime.event_bus import EventBus
from runtime.listeners import ConsoleEventListener
from runtime.logging_listener import LoggingEventListener
from runtime.metrics_listener import MetricsListener
from runtime.audit_listener import AuditListener
from runtime.runtime_config import RuntimeConfig



conversation = []

print("Type 'exit' to quit.\n")

bus = EventBus()
metrics = MetricsListener()
audit = AuditListener()
bus.subscribe(ConsoleEventListener())
bus.subscribe(
    LoggingEventListener()
)
bus.subscribe(metrics)
bus.subscribe(audit)

while True:

    question = input("You: ")

    if question.lower() == "exit":
        break

    conversation.append(
        HumanMessage(content=question)
    )

    workflow_id = str(uuid.uuid4())

    state = {
        "workflow_id": workflow_id,
        "messages": conversation,
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
        "event_bus": bus,      # <-- Add this here        
    
    }
    print(workflow_id)
    result = app.invoke(state)
    print(metrics.snapshot())
    for event in audit.history():
        print(
            event.timestamp,
            event.type,
            event.step_id,
            event.tool,
        )
    print(result)
    conversation = result["messages"]
   

    print("\nAssistant:")
    print(conversation[-1].content)
    print("-" * 50)
