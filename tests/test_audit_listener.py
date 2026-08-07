from runtime.audit_listener import AuditListener
from runtime.event import WorkflowEvent
from shared_types.workflow_event_type import WorkflowEventType



def test_audit_listener_records_events():

    listener = AuditListener()

    event1 = WorkflowEvent(
        type=WorkflowEventType.WORKFLOW_STARTED,
    )

    event2 = WorkflowEvent(
        type=WorkflowEventType.WORKFLOW_COMPLETED,
    )

    listener(event1)
    listener(event2)

    history = listener.history()

    assert len(history) == 2
    assert history[0] == event1
    assert history[1] == event2

def test_audit_listener_clear():

    listener = AuditListener()

    listener(
        WorkflowEvent(
            type=WorkflowEventType.WORKFLOW_STARTED,
        )
    )

    listener.clear()

    assert listener.history() == []