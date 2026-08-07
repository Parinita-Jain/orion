from runtime.event import WorkflowEvent
from runtime.event_bus import EventBus
from shared_types.workflow_event_type import WorkflowEventType


def test_listener_receives_event():

    received = []

    def listener(event):

        received.append(event)

    bus = EventBus()

    bus.subscribe(listener)

    event = WorkflowEvent(
        type=WorkflowEventType.STEP_STARTED,
        step_id=1,
        tool="echo",
    )

    bus.emit(event)

    assert len(received) == 1

    assert received[0].type == WorkflowEventType.STEP_STARTED

    assert received[0].step_id == 1

def test_multiple_listeners():

    first = []

    second = []

    bus = EventBus()

    bus.subscribe(first.append)

    bus.subscribe(second.append)

    event = WorkflowEvent(
        type=WorkflowEventType.WORKFLOW_STARTED,
    )

    bus.emit(event)

    assert len(first) == 1

    assert len(second) == 1

def test_timestamp_added():

    bus = EventBus()

    received = []

    bus.subscribe(received.append)

    event = WorkflowEvent(
        type=WorkflowEventType.WORKFLOW_STARTED,
    )

    bus.emit(event)

    assert received[0].timestamp > 0