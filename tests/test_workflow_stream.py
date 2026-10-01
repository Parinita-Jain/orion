from threading import Event

from unittest.mock import patch

from runtime.event import WorkflowEvent
from runtime.event_bus import EventBus
from runtime.stream import stream_workflow
from shared_types.workflow_event_type import WorkflowEventType


class FakeApp:
    def __init__(self):
        self.started = Event()
        self.release = Event()

    def invoke(self, state):
        event_bus: EventBus = state["event_bus"]

        event_bus.emit(
            WorkflowEvent(
                type=WorkflowEventType.WORKFLOW_STARTED,
            )
        )

        self.started.set()
        self.release.wait(timeout=2)

        event_bus.emit(
            WorkflowEvent(
                type=WorkflowEventType.WORKFLOW_COMPLETED,
            )
        )

        return {
            **state,
            "done": True,
            "output": {"answer": "finished"},
        }


def test_workflow_stream_delivers_events_before_execution_completes():
    fake_app = FakeApp()

    with patch("runtime.stream.app", fake_app):
        stream = stream_workflow(
            {
                "workflow_id": "stream-test",
            }
        )

        assert fake_app.started.wait(timeout=2)

        first_event = next(stream)

        assert first_event.type == WorkflowEventType.WORKFLOW_STARTED
        assert stream.result is None
        assert stream.error is None

        fake_app.release.set()

        remaining_events = list(stream)

    assert [
        event.type
        for event in [first_event, *remaining_events]
    ] == [
        WorkflowEventType.WORKFLOW_STARTED,
        WorkflowEventType.WORKFLOW_COMPLETED,
    ]

    assert stream.result is not None
    assert stream.result["done"] is True
    assert stream.result["output"] == {"answer": "finished"}
    assert stream.done is True


def test_workflow_stream_captures_worker_error():
    class FailingApp:
        def invoke(self, state):
            raise RuntimeError("stream failure")

    with patch("runtime.stream.app", FailingApp()):
        stream = stream_workflow(
            {
                "workflow_id": "stream-error-test",
            }
        )

        assert list(stream) == []

    assert isinstance(stream.error, RuntimeError)
    assert str(stream.error) == "stream failure"
    assert stream.result is None
    assert stream.done is True


def test_workflow_streams_agent_events():
    class AgentApp:
        def invoke(self, state):
            state["event_bus"].emit(
                WorkflowEvent(
                    type=WorkflowEventType.AGENT_MESSAGE,
                    agent_task_id="task-1",
                    agent_id="researcher",
                    payload={
                        "message": "Research completed",
                    },
                )
            )

            return {
                **state,
                "done": True,
            }

    with patch("runtime.stream.app", AgentApp()):
        stream = stream_workflow(
            {
                "workflow_id": "agent-stream-test",
            }
        )

        events = list(stream)

    assert len(events) == 1
    assert events[0].type == WorkflowEventType.AGENT_MESSAGE
    assert events[0].agent_task_id == "task-1"
    assert events[0].agent_id == "researcher"
    assert events[0].payload == {
        "message": "Research completed",
    }


def test_workflow_streams_are_isolated():
    class IsolatedApp:
        def invoke(self, state):
            workflow_id = state["workflow_id"]

            state["event_bus"].emit(
                WorkflowEvent(
                    type=WorkflowEventType.WORKFLOW_STARTED,
                    payload={"workflow_id": workflow_id},
                )
            )

            return {
                **state,
                "done": True,
            }

    with patch("runtime.stream.app", IsolatedApp()):
        first = stream_workflow({"workflow_id": "workflow-1"})
        second = stream_workflow({"workflow_id": "workflow-2"})

        first_events = list(first)
        second_events = list(second)

    assert first_events[0].payload == {
        "workflow_id": "workflow-1",
    }
    assert second_events[0].payload == {
        "workflow_id": "workflow-2",
    }

def test_stream_event_bus_isolation():
    """Each WorkflowStream receives only events from its own EventBus."""

    from unittest.mock import patch

    from runtime.event import WorkflowEvent
    from runtime.stream import stream_workflow
    from shared_types.workflow_event_type import WorkflowEventType

    state_a = {
        "workflow_id": "stream-isolation-a",
    }

    state_b = {
        "workflow_id": "stream-isolation-b",
    }

    event_a = WorkflowEvent(
        type=WorkflowEventType.WORKFLOW_STARTED,
        payload={"workflow_id": "stream-isolation-a"},
    )

    event_b = WorkflowEvent(
        type=WorkflowEventType.WORKFLOW_STARTED,
        payload={"workflow_id": "stream-isolation-b"},
    )

    def fake_invoke(state):
        event_bus = state["event_bus"]

        if state["workflow_id"] == "stream-isolation-a":
            event_bus.emit(event_a)
        else:
            event_bus.emit(event_b)

        return state

    with patch("runtime.stream.app.invoke", side_effect=fake_invoke):
        stream_a = stream_workflow(state_a)
        stream_b = stream_workflow(state_b)

        events_a = list(stream_a)
        events_b = list(stream_b)

    assert events_a == [event_a]
    assert events_b == [event_b]

    assert stream_a.result["workflow_id"] == "stream-isolation-a"
    assert stream_b.result["workflow_id"] == "stream-isolation-b"