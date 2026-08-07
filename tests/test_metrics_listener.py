from runtime.event import WorkflowEvent

from shared_types.workflow_event_type import WorkflowEventType
from runtime.metrics_listener import MetricsListener


def test_metrics_listener_counts_events():

    listener = MetricsListener()

    listener(
        WorkflowEvent(
            type=WorkflowEventType.WORKFLOW_STARTED,
        )
    )

    listener(
        WorkflowEvent(
            type=WorkflowEventType.STEP_STARTED,
        )
    )

    listener(
        WorkflowEvent(
            type=WorkflowEventType.STEP_COMPLETED,
        )
    )

    listener(
        WorkflowEvent(
            type=WorkflowEventType.WORKFLOW_COMPLETED,
        )
    )

    metrics = listener.snapshot()

    assert metrics["workflows_started"] == 1
    assert metrics["workflows_completed"] == 1
    assert metrics["steps_started"] == 1
    assert metrics["steps_completed"] == 1
    assert metrics["steps_failed"] == 0
    assert metrics["steps_skipped"] == 0