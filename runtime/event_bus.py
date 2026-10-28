
from runtime.event import WorkflowEvent


class EventBus:

    def __init__(self):
        self._listeners = []

    def subscribe(self, listener):
        self._listeners.append(listener)

    def unsubscribe(self, listener):
        """Remove a subscribed listener without affecting others."""
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    def emit(self, event: WorkflowEvent):
        for listener in self._listeners:
            listener(event)
