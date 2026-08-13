import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.messages import AIMessage

from models.execution_record import ExecutionRecord

from registry import get_tool

from utils import (
    get_ready_steps,
    resolve_context_variables,
    resolve_step_references,
)
from config import logger
from runtime.retry import execute_with_retry

from executor.execution_summary import ExecutionSummary
from shared_types.step_status import StepStatus

from runtime.event import WorkflowEvent
from runtime.event_bus import EventBus
from shared_types.workflow_event_type import WorkflowEventType

from runtime.timeout import run_with_timeout
from concurrent.futures import TimeoutError

from shared_types.failure_reason import FailureReason
from runtime.retry_error import RetryError

from runtime.approval_decision import ApprovalDecision

from condition import evaluate_condition

from persistence import save_workflow

def execute_step(step, state, tool_results):

    tool_name = step.tool

    tool_input = resolve_step_references(
        step.tool_input,
        tool_results,
    )

    tool_input = resolve_context_variables(
        tool_input,
        state["context"],
    )

    logger.debug("Original input: %s", step.tool_input)
    logger.debug("Resolved input: %s", tool_input)

    tool_state = {
        **state,
        "tool_input": tool_input,
    }

    tool = get_tool(tool_name)

    if tool is None:
        raise ValueError(
        f"Tool '{tool_name}' is not registered."
    )

    config = state["runtime_config"]

    max_retries = (
        tool.retries
        if tool.retries is not None
        else config.default_retries
    )

    timeout = (
        tool.timeout
        if tool.timeout is not None
        else config.default_timeout
    )

    tool_function = tool.function

    if tool_function is None:
        raise ValueError(
                f"Tool '{tool_name}' has no registered function."
            )

    start_time = time.perf_counter()

    try:

        if timeout is None:

            result = execute_with_retry(
                tool_function,
                tool_state,
                tool_name=tool_name,
                max_retries=max_retries,
            )

        else:

            result = run_with_timeout(
                execute_with_retry,
                tool_function,
                tool_state,
                tool_name=tool_name,
                max_retries=max_retries,
                timeout=timeout,
            )
        if result["success"]:
            result["status"] = StepStatus.SUCCESS
        else:
            result["status"] = StepStatus.FAILED

        if result["success"]:
            logger.info(
                "Tool '%s' completed successfully.",
                tool_name,
            )
        else:
            logger.warning(
                "Tool '%s' completed with failure: %s",
                tool_name,
                result["error"],
            )

        end_time = time.perf_counter()

        duration = end_time - start_time

        record = ExecutionRecord(
            step_id=step.id,
            tool=tool_name,
            success=result.get("success", True),
            retries=0,          # we'll improve this later
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            error=result.get("error"),
        )

        return {
            "result": result,
            "record": record,
        }
        
    
    except TimeoutError as e:

            end_time = time.perf_counter()

            duration = end_time - start_time

            record = ExecutionRecord(
                step_id=step.id,
                tool=tool_name,
                success=False,
                retries=max_retries,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error=str(e),
            )

            return {
                "result": {
                    "messages": [
                        AIMessage(
                            content="Tool execution timed out."
                        )
                    ],
                    "output": {},
                    "success": False,
                    "status": StepStatus.FAILED,
                    "failure_reason": FailureReason.TIMEOUT,
                    "error": str(e),
                },
                "record": record,
            }
    

    except Exception as e:

        if isinstance(e, RetryError):
            retries = e.retries
            error = str(e.original_exception)
            failure_reason = FailureReason.EXCEPTION
        else:
            retries = 0
            error = str(e)
            failure_reason = FailureReason.EXCEPTION

        end_time = time.perf_counter()

        duration = end_time - start_time

        record = ExecutionRecord(
            step_id=step.id,
            tool=tool_name,
            success=False,
            retries=retries,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            error=error
        )

        return {
            "result": {
                "messages": [
                    AIMessage(
                        content="Tool execution failed."
                    )
                ],
                "output": {},
                "success": False,
                "status": StepStatus.FAILED,
                "failure_reason": FailureReason.EXCEPTION,
                "error": error,
            },
            "record": record,
        }

    

def failed_dependencies(step, tool_results):
    """
    Returns a list of dependency IDs that truly failed.
    """

    failed = []

    for dep in step.depends_on:

        result = tool_results.get(dep)

        if result is None:
            continue

        if result["status"] in (
            StepStatus.FAILED,
            StepStatus.SKIPPED,
        ):
            failed.append(dep)

    return failed

def executor_node(state):

    approval_request = None
    logger.info("Executor started")
    config = state["runtime_config"]
    approval_decision = state.get(
        "approval_decision"
    )
    event_bus = state.setdefault(
        "event_bus",
        EventBus(),
    )
    event_bus.emit(
        WorkflowEvent(
            type=WorkflowEventType.WORKFLOW_STARTED,
        )
    )
    execution_records = state.get(
        "execution_records",
        [],
    )

    tool_results = state.get(
        "tool_results",
        {},
    )

    completed_steps = {
        step_id
        for step_id, result in tool_results.items()
        if result["success"]
    }

    logger.debug(
        "Resuming with completed steps: %s",
        sorted(completed_steps),
    )
    state["context"] = state.get(
        "context",
        {},
    )
    
    logger.debug("Execution steps: %s", state["steps"])
    pending_steps = [
        step
        for step in state["steps"]
        if step.id not in completed_steps
    ]

    while pending_steps:

        ready_steps = get_ready_steps(
            pending_steps,
            completed_steps,
        )

        if not ready_steps:

            print("tool_results =", tool_results)

            blocked_steps = [
                step
                for step in pending_steps
                if failed_dependencies(step, tool_results)
            ]

            if blocked_steps:

                logger.info(
                    "Skipping %d blocked step(s).",
                    len(blocked_steps),
                )

                for step in blocked_steps:

                    failed = failed_dependencies(
                            step,
                            tool_results,
                        )

                    tool_results[step.id] = {
                        "messages": [
                            AIMessage(
                                content=(
                                    f"Step {step.id} skipped because "
                                    f"dependencies {failed} failed."
                                )
                            )
                        ],
                         "output": {},
                         "success": False,
                         "status": StepStatus.SKIPPED,
                         "error": (
                            f"Skipped because dependencies "
                            f"{failed} failed."
                        ),
                    }
                    event_bus.emit(
                        WorkflowEvent(
                            type=WorkflowEventType.STEP_SKIPPED,
                            step_id=step.id,
                            tool=step.tool,
                        )
                    )

                    execution_records.append(
                        ExecutionRecord(
                            step_id=step.id,
                            tool=step.tool,
                            success=False,
                            retries=0,
                            start_time=0,
                            end_time=0,
                            duration=0,
                            error=(
                                f"Skipped because dependencies "
                                f"{failed} failed."
                            ),
                        )
                    )

                    pending_steps.remove(step)

                continue

            waiting_for_approval = any(
                any(
                    tool_results.get(dep, {}).get("status")
                    == StepStatus.WAITING_FOR_APPROVAL
                    for dep in step.depends_on
                )
                for step in pending_steps
            )

            if waiting_for_approval:

                logger.info(
                    "Workflow paused waiting for approval."
                )

                break

            raise ValueError(
                f"No executable step found.\n"
                f"Completed: {completed_steps}\n"
                f"Pending: {[step.id for step in pending_steps]}"
            )

        
        logger.info(
                    "Executing %d ready step(s)",
                    len(ready_steps),
                    )
        logger.debug("Ready steps: %s", ready_steps)
                   

        with ThreadPoolExecutor(
            max_workers=config.max_parallel_workers,
            ) as executor:

            futures = {}

            for step in ready_steps:

                logger.info(
                "Submitting step %d (%s)",
                step.id,
                step.tool,
                )   
                event_bus.emit(
                    WorkflowEvent(
                        type=WorkflowEventType.STEP_STARTED,
                        step_id=step.id,
                        tool=step.tool,
                    )
                )

                if step.approval is not None:

                    if approval_decision is None:

                        approval_request = step.approval

                        tool_results[step.id] = {
                            "messages": [],
                            "output": {},
                            "success": False,
                            "status": StepStatus.WAITING_FOR_APPROVAL,
                            "error": None,
                        }

                        pending_steps.remove(step)

                        continue

                    if approval_decision == ApprovalDecision.REJECTED:

                        tool_results[step.id] = {
                            "messages": [
                                AIMessage(
                                    content="Approval rejected."
                                )
                            ],
                            "output": {},
                            "success": False,
                            "status": StepStatus.FAILED,
                            "error": "Approval rejected.",
                        }

                        execution_records.append(
                            ExecutionRecord(
                                step_id=step.id,
                                tool=step.tool,
                                success=False,
                                retries=0,
                                start_time=0,
                                end_time=0,
                                duration=0,
                                error="Approval rejected.",
                            )
                        )

                        pending_steps.remove(step)

                        continue

                    # APPROVED
                    # Fall through to normal execution.

                if (
                    step.condition is not None
                    and not evaluate_condition(
                        step.condition,
                        tool_results,
                    )
                ):

                    tool_results[step.id] = {
                        "messages": [
                            AIMessage(
                                content="Condition evaluated to false."
                            )
                        ],
                        "output": {},
                        "success": True,
                        "status": StepStatus.SKIPPED,
                        "error": None,
                    }

                    execution_records.append(
                        ExecutionRecord(
                            step_id=step.id,
                            tool=step.tool,
                            success=True,
                            retries=0,
                            start_time=0,
                            end_time=0,
                            duration=0,
                            error=None,
                        )
                    )

                    pending_steps.remove(step)

                    logger.info(
                        "Skipped step %d because condition was false.",
                        step.id,
                    )

                    continue

                future = executor.submit(
                    execute_step,
                    step,
                    state,
                    tool_results,
                )

                futures[future] = step

            for future in as_completed(futures):

                step = futures[future]

                try:

                    execution = future.result()
                    result = execution["result"]
                    
                    record = execution["record"]
                    if result["success"]:

                        event_bus.emit(
                            WorkflowEvent(
                                type=WorkflowEventType.STEP_COMPLETED,
                                step_id=step.id,
                                tool=step.tool,
                            )
                        )

                    else:

                        reason = result.get(
                            "failure_reason",
                            FailureReason.EXCEPTION,
                        )
                        

                        event_bus.emit(
                            WorkflowEvent(
                                type=WorkflowEventType.STEP_FAILED,
                                step_id=step.id,
                                tool=step.tool,
                                payload={
                                    "reason": reason,
                                },
                            )
                        )                  

                except Exception as e:
                    
                    logger.exception(
                        "Step %d execution failed",
                        step.id,
                    )
                    event_bus.emit(
                                    WorkflowEvent(
                                                    type=WorkflowEventType.STEP_FAILED,
                                                    step_id=step.id,
                                                    tool=step.tool,
                                                )
                                )          
                    result = {
                        "messages": [
                            AIMessage(
                                content=f"Step {step.id} failed."
                            )
                        ],
                        "output": {},
                        "success": False,
                        "status": StepStatus.FAILED,
                        "failure_reason": FailureReason.EXCEPTION,
                        "error": str(e),
                    }

                    record = ExecutionRecord(
                        step_id=step.id,
                        tool=step.tool,
                        success=False,
                        retries=0,
                        start_time=0,
                        end_time=0,
                        duration=0,
                        error=str(e),
                    )

                execution_records.append(record)

                tool_results[step.id] = result

                if result["success"]:

                    output = result["output"]

                    state["context"][
                        f"step_{step.id}"
                    ] = output

                    if step.output:

                        first_value = next(
                            iter(output.values())
                        )

                        state["context"][
                            step.output
                        ] = first_value

                
                    completed_steps.add(step.id)

                    # -----------------------------
                    # Sprint 10 - Step Supersession
                    # -----------------------------
                    if (
                        step.replaces is not None
                        and step.replaces in tool_results
                    ):

                        original = tool_results[
                            step.replaces
                        ]

                        original["status"] = StepStatus.SUPERSEDED

                        logger.info(
                            "Step %d superseded by step %d",
                            step.replaces,
                            step.id,
                        )

                if step in pending_steps:
                    pending_steps.remove(step)

                if result["success"]:
                    logger.info(
                        "Completed step %d",
                        step.id,
                    )
                else:
                    logger.info(
                        "Step %d finished with status %s",
                        step.id,
                        result["status"],
                    )

                logger.debug(
                    "Context updated after step %d: %s",
                    step.id,
                    list(state["context"].keys()),
                )

        

    state["tool_results"] = tool_results
    state["execution_records"] = execution_records

    for record in execution_records:

        logger.debug(
            "Step %d | %s | %.3fs | Retries=%d | %s",
            record.step_id,
            record.tool,
            record.duration,
            record.retries,
            "Success" if record.success else "Failed",
        )

    total_time = sum(
        record.duration
        for record in execution_records
    )
    success_count = sum(
    1
    for result in tool_results.values()
    if result.get("status") == StepStatus.SUCCESS
    )

    failed_count = sum(
        1
        for result in tool_results.values()
        if result.get("status") == StepStatus.FAILED
    )

    skipped_count = sum(
        1
        for result in tool_results.values()
        if result.get("status") == StepStatus.SKIPPED
    )

    summary = ExecutionSummary(
        total_steps=len(tool_results),
        succeeded=success_count,
        failed=failed_count,
        skipped=skipped_count,
        duration=total_time,
    )
    
    logger.info(
        "Total execution time: %.3fs",
        total_time,
               )

    event_bus.emit(
        WorkflowEvent(
            type=WorkflowEventType.WORKFLOW_COMPLETED,
        )
    )


    save_workflow(
        state["workflow_id"],
        state,
    )
    
    return {
        "tool_results": tool_results,
        "execution_records": execution_records,
        "execution_summary": summary,
        "context": state["context"],
        "approval_request": approval_request,
    }