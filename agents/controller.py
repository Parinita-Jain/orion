from typing import Any

from agents.decision import (
    AgentAction,
    AgentDecision,
)

from agents.message import AgentMessage

from agents.models import AgentDefinition

from agents.registry import (
    get_agent,
    register_agent,
)

from agents.task import (
    AgentTask,
    AgentTaskStatus,
)

from agents.task_manager import (
    complete_task,
    create_child_task,
    get_parent_task,
    get_task,
    start_task,
)


SUPERVISOR_AGENT = AgentDefinition(
    id="supervisor",
    name="Supervisor Agent",
    role="supervisor",
    instructions=(
        "Coordinate the user's request, determine the required work, "
        "and delegate work to specialized agents when appropriate."
    ),
)


def get_supervisor_agent():
    """
    Return the registered supervisor, registering the default supervisor
    definition when necessary.
    """

    agent = get_agent(
        SUPERVISOR_AGENT.id
    )

    if agent is None:
        register_agent(
            SUPERVISOR_AGENT
        )
        agent = SUPERVISOR_AGENT

    return agent


def _next_task_id(
    agent_tasks: dict[str, AgentTask],
) -> str:

    number = 1

    while f"T{number}" in agent_tasks:
        number += 1

    return f"T{number}"


def _find_root_task(
    agent_tasks: dict[str, AgentTask],
) -> AgentTask | None:

    for task in agent_tasks.values():

        if task.parent_task_id is None:
            return task

    return None


def ensure_active_task(
    agent_tasks: dict[str, AgentTask],
    agent_messages: list[AgentMessage],
    current_task_id: str | None,
    messages: Any,
) -> AgentTask:
    """
    Resolve the current task or create the workflow root Supervisor task.
    """

    task = None

    if current_task_id is not None:
        task = agent_tasks.get(
            current_task_id
        )

    if task is None:
        task = _find_root_task(
            agent_tasks
        )

    if task is None:

        if not messages:
            raise ValueError(
                "Cannot create supervisor task without a user message."
            )

        request = messages[-1].content

        get_supervisor_agent()

        task_id = _next_task_id(
            agent_tasks
        )

        task = AgentTask(
            task_id=task_id,
            parent_task_id=None,
            agent_id=SUPERVISOR_AGENT.id,
            request=request,
            status=AgentTaskStatus.ASSIGNED,
        )

        agent_tasks[task_id] = task

    return task


def get_task_steps(
    state,
    task_id: str,
):
    """
    Return PlanSteps belonging to one AgentTask.
    """

    return [
        step
        for step in state.get("steps", [])
        if step.agent_task_id == task_id
    ]


def build_decision_context(
    task: AgentTask,
    state,
) -> str:
    """
    Build context describing work already performed by this task.
    """

    sections = []

    task_steps = get_task_steps(
        state,
        task.task_id,
    )

    tool_results = state.get(
        "tool_results",
        {},
    )

    if task_steps:

        execution_lines = []

        for step in task_steps:

            result = tool_results.get(
                step.id
            )

            if result is None:
                execution_lines.append(
                    f"""
Step {step.id}
Tool: {step.tool}
Status: pending
"""
                )
                continue

            execution_lines.append(
                f"""
Step {step.id}
Tool: {step.tool}
Status: {result.get("status")}
Success: {result.get("success")}
Output: {result.get("output")}
Error: {result.get("error")}
Failure Reason: {result.get("failure_reason")}
"""
            )

        sections.append(
            "Current Task Execution:\n"
            + "\n".join(execution_lines)
        )

    child_results = task.metadata.get(
        "child_results",
        [],
    )

    if child_results:

        child_lines = []

        for child in child_results:

            child_lines.append(
                f"""
Task ID: {child.get("task_id")}
Agent ID: {child.get("agent_id")}
Request: {child.get("request")}
Status: {child.get("status", "completed")}
Result: {child.get("result")}
"""
            )

        sections.append(
            "Child Task Results:\n"
            + "\n".join(child_lines)
        )

    if not sections:
        return (
            "No execution or child-task results are available yet."
        )

    return "\n\n".join(
        sections
    )


def _default_task_result(
    task: AgentTask,
    state,
) -> dict[str, Any]:
    """
    Build a useful result when the agent completes without explicitly
    supplying a result.
    """

    task_steps = get_task_steps(
        state,
        task.task_id,
    )

    tool_results = state.get(
        "tool_results",
        {},
    )

    outputs = []

    for step in task_steps:

        result = tool_results.get(
            step.id
        )

        if result is None:
            continue

        if result.get("success"):
            outputs.append(
                {
                    "step_id": step.id,
                    "tool": step.tool,
                    "output": result.get("output"),
                }
            )

    return {
        "task_id": task.task_id,
        "agent_id": task.agent_id,
        "outputs": outputs,
    }


def process_agent_decision(
    agent_tasks: dict[str, AgentTask],
    agent_messages: list[AgentMessage],
    current_task_id: str,
    state,
    decision: AgentDecision,
):
    """
    Apply an AgentDecision to workflow-level AgentTask state.

    Returns the next graph destination and updated agent state.
    """

    task = get_task(
        agent_tasks,
        current_task_id,
    )

    if decision.action == AgentAction.PLAN:

        return {
            "agent_tasks": agent_tasks,
            "agent_messages": agent_messages,
            "current_agent_task_id": task.task_id,
            "agent_next_node": "planner",
            "error": None,
        }

    if decision.action == AgentAction.DELEGATE:

        existing_steps = get_task_steps(
            state,
            task.task_id,
        )

        if existing_steps:
            raise ValueError(
                f"AgentTask '{task.task_id}' cannot delegate after "
                "its own PlanSteps have started."
            )

        child = create_child_task(
            agent_tasks=agent_tasks,
            parent_task_id=task.task_id,
            agent_id=decision.target_agent_id,
            request=decision.request,
        )

        start_task(
            agent_tasks,
            child.task_id,
        )

        agent_messages.append(
            AgentMessage(
                message_id=f"delegation-{child.task_id}",
                sender=task.agent_id,
                recipient=child.agent_id,
                content=child.request,
                task_id=child.task_id,
            )
        )

        return {
            "agent_tasks": agent_tasks,
            "agent_messages": agent_messages,
            "current_agent_task_id": child.task_id,
            "agent_next_node": "agent",
            "error": None,
        }

    if decision.action == AgentAction.COMPLETE:

        result = decision.result

        if result is None:
            result = _default_task_result(
                task,
                state,
            )

        parent = get_parent_task(
            agent_tasks,
            task.task_id,
        )

        complete_task(
            agent_tasks,
            task.task_id,
            result=result,
        )

        if parent is not None:

            agent_messages.append(
                AgentMessage(
                    message_id=f"result-{task.task_id}",
                    sender=task.agent_id,
                    recipient=parent.agent_id,
                    content=result,
                    task_id=task.task_id,
                )
            )

            return {
                "agent_tasks": agent_tasks,
                "agent_messages": agent_messages,
                "current_agent_task_id": parent.task_id,
                "agent_next_node": "agent",
                "error": None,
            }

        return {
            "agent_tasks": agent_tasks,
            "agent_messages": agent_messages,
            "current_agent_task_id": task.task_id,
            "agent_next_node": "synthesizer",
            "error": None,
        }

    raise ValueError(
        f"Unsupported AgentAction: {decision.action}"
    )