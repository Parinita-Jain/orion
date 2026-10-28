from __future__ import annotations

from queue import Queue
from threading import Thread
from typing import Any, Iterator

from runtime.event import WorkflowEvent
from runtime.event_bus import EventBus
from workflow.graph import app


_STREAM_END = object()


class WorkflowStream(Iterator[WorkflowEvent]):
    """Stream WorkflowEvents while a workflow executes in the background."""

    def __init__(
        self,
        state: dict[str, Any],
        event_bus: EventBus | None = None,
    ):
        self._queue: Queue[WorkflowEvent | object] = Queue()
        self._result: dict[str, Any] | None = None
        self._error: BaseException | None = None

        execution_state = dict(state)
        self._event_bus = event_bus if event_bus is not None else EventBus()
        self._listener = self._queue.put
        self._event_bus.subscribe(self._listener)
        execution_state["event_bus"] = self._event_bus

        self._thread = Thread(
            target=self._run,
            args=(execution_state,),
            name="orion-workflow-stream",
            daemon=True,
        )
        self._thread.start()

    def _run(self, state: dict[str, Any]) -> None:
        try:
            self._result = app.invoke(state)
        except BaseException as exc:
            self._error = exc
        finally:
            self._event_bus.unsubscribe(self._listener)
            self._queue.put(_STREAM_END)

    def __iter__(self) -> WorkflowStream:
        return self

    def __next__(self) -> WorkflowEvent:
        item = self._queue.get()

        if item is _STREAM_END:
            raise StopIteration

        return item

    def close(self) -> None:
        """Stop receiving events without forcibly terminating the workflow."""
        if self._event_bus is not None and self._listener is not None:
            self._event_bus.unsubscribe(self._listener)

    @property
    def result(self) -> dict[str, Any] | None:
        """Final workflow state, available after execution completes."""
        return self._result

    @property
    def error(self) -> BaseException | None:
        """Unhandled exception raised by the workflow, if any."""
        return self._error

    @property
    def done(self) -> bool:
        if self._thread is None:
            return True

        return not self._thread.is_alive()

    @classmethod
    def completed(
        cls,
        state: dict[str, Any],
    ) -> WorkflowStream:
        stream = cls.__new__(cls)

        stream._queue = Queue()
        stream._result = state
        stream._error = None
        stream._event_bus = None
        stream._listener = None
        stream._thread = None

        stream._queue.put(_STREAM_END)

        return stream

def stream_workflow(
    state: dict[str, Any],
    event_bus: EventBus | None = None,
) -> WorkflowStream:
    """Execute a workflow while yielding its runtime WorkflowEvents."""
    return WorkflowStream(state, event_bus=event_bus)