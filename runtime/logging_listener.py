import logging

from runtime.event import WorkflowEvent

from shared_types.workflow_event_type import WorkflowEventType
from shared_types.failure_reason import FailureReason

logger = logging.getLogger(__name__)


class LoggingEventListener:

    def __call__(self, event: WorkflowEvent):

        match event.type:

            case WorkflowEventType.WORKFLOW_STARTED:
                logger.info("Workflow started.")

            case WorkflowEventType.WORKFLOW_COMPLETED:
                logger.info("Workflow completed.")

            case WorkflowEventType.STEP_STARTED:
                logger.info(
                    "Step %s started (%s).",
                    event.step_id,
                    event.tool,
                )

            case WorkflowEventType.STEP_COMPLETED:
                logger.info(
                    "Step %s completed (%s).",
                    event.step_id,
                    event.tool,
                )

            case WorkflowEventType.STEP_FAILED:

                reason = event.payload.get("reason")

                if reason == FailureReason.TIMEOUT:

                    logger.warning(
                        "Step %s timed out (%s).",
                        event.step_id,
                        event.tool,
                    )

                else:

                    logger.error(
                        "Step %s failed (%s).",
                        event.step_id,
                        event.tool,
                    )