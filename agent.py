from agents.controller import (
    SUPERVISOR_AGENT,
    build_decision_context,
    ensure_active_task,
    fail_agent_task,
    get_task_steps,
    process_agent_decision,
    start_agent_task,
)

from runtime.event_bus import EventBus

from agents.task import AgentTaskStatus

from errors import (
    ErrorType,
    OrionError,
)


def agent_node(state):

    print("\n===== AGENT NODE =====")

    agent_tasks = dict(
        state.get(
            "agent_tasks",
            {},
        )
    )

    agent_messages = list(
        state.get(
            "agent_messages",
            [],
        )
    )

    messages = state.get(
        "messages",
        [],
    )

    current_task_id = state.get(
        "current_agent_task_id"
    )

    event_bus = state.setdefault(
        "event_bus",
        EventBus(),
    )

    task = None

    try:

        task = ensure_active_task(
            agent_tasks=agent_tasks,
            agent_messages=agent_messages,
            current_task_id=current_task_id,
            messages=messages,
            event_bus=event_bus,
        )

        start_agent_task(
            agent_tasks,
            task.task_id,
            event_bus=event_bus,
        )

        decision_context = build_decision_context(
            task,
            state,
        )

        allow_delegation = not bool(
            get_task_steps(
                state,
                task.task_id,
            )
        )

        from agents.runtime import AgentRuntime

        runtime = AgentRuntime()

        decision = runtime.decide_task(
            task,
            decision_context=decision_context,
            allow_delegation=allow_delegation,
        )

        return process_agent_decision(
            agent_tasks=agent_tasks,
            agent_messages=agent_messages,
            current_task_id=task.task_id,
            state=state,
            decision=decision,
            event_bus=event_bus,
        )

    except Exception as e:
        if (
            task is not None
            and task.status == AgentTaskStatus.RUNNING
        ):
            fail_agent_task(
                agent_tasks,
                task.task_id,
                error=str(e),
                event_bus=event_bus,
            )

        return {
            "agent_tasks": agent_tasks,
            "agent_messages": agent_messages,
            "current_agent_task_id": current_task_id,
            "agent_next_node": "error",
            "error": OrionError(
                source="agent",
                error_type=ErrorType.PLANNER,
                message=str(e),
                recoverable=True,
                original_exception=e,
            ),
        }