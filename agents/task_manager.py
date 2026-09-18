from typing import Any

from agents.registry import get_agent
from agents.task import (
    AgentTask,
    AgentTaskStatus,
)


def next_task_id(
    agent_tasks: dict[str, AgentTask],
) -> str:
    """
    Generate the next workflow-local AgentTask ID.
    """

    number = 1

    while f"T{number}" in agent_tasks:
        number += 1

    return f"T{number}"


def get_task(
    agent_tasks: dict[str, AgentTask],
    task_id: str,
) -> AgentTask:
    """
    Return a task by ID or raise a clear error.
    """

    task = agent_tasks.get(task_id)

    if task is None:
        raise ValueError(
            f"AgentTask '{task_id}' does not exist."
        )

    return task


def get_parent_task(
    agent_tasks: dict[str, AgentTask],
    task_id: str,
) -> AgentTask | None:
    """
    Return the parent task for a task, if one exists.
    """

    task = get_task(
        agent_tasks,
        task_id,
    )

    if task.parent_task_id is None:
        return None

    return get_task(
        agent_tasks,
        task.parent_task_id,
    )


def create_child_task(
    agent_tasks: dict[str, AgentTask],
    parent_task_id: str,
    agent_id: str,
    request: str,
) -> AgentTask:
    """
    Create a child AgentTask delegated by a parent task.
    """

    parent = get_task(
        agent_tasks,
        parent_task_id,
    )

    if parent.status in (
        AgentTaskStatus.COMPLETED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
    ):
        raise ValueError(
            f"Cannot create a child task for "
            f"AgentTask '{parent_task_id}' because "
            f"the parent task is {parent.status.value}."
        )

    if not request or not request.strip():
        raise ValueError(
            "Child AgentTask request must not be empty."
        )

    if get_agent(agent_id) is None:
        raise ValueError(
            f"Agent '{agent_id}' is not registered."
        )

    task_id = next_task_id(
        agent_tasks
    )

    child = AgentTask(
        task_id=task_id,
        parent_task_id=parent_task_id,
        agent_id=agent_id,
        request=request,
        status=AgentTaskStatus.ASSIGNED,
        metadata={
            "delegated_by": parent_task_id,
        },
    )

    agent_tasks[task_id] = child

    return child


def start_task(
    agent_tasks: dict[str, AgentTask],
    task_id: str,
) -> AgentTask:
    """
    Move an assigned task into RUNNING state.
    """

    task = get_task(
        agent_tasks,
        task_id,
    )

    if task.status not in (
        AgentTaskStatus.CREATED,
        AgentTaskStatus.ASSIGNED,
    ):
        raise ValueError(
            f"AgentTask '{task_id}' cannot be started "
            f"from status {task.status.value}."
        )

    task.status = AgentTaskStatus.RUNNING

    return task


def complete_task(
    agent_tasks: dict[str, AgentTask],
    task_id: str,
    result: Any = None,
) -> AgentTask:
    """
    Complete a task and attach its result to its parent.
    """

    task = get_task(
        agent_tasks,
        task_id,
    )

    if task.status not in (
        AgentTaskStatus.ASSIGNED,
        AgentTaskStatus.RUNNING,
    ):
        raise ValueError(
            f"AgentTask '{task_id}' cannot be completed "
            f"from status {task.status.value}."
        )

    task.status = AgentTaskStatus.COMPLETED
    task.result = result

    parent = get_parent_task(
        agent_tasks,
        task_id,
    )

    if parent is not None:
        child_results = parent.metadata.setdefault(
            "child_results",
            [],
        )

        child_results.append(
            {
                "task_id": task.task_id,
                "agent_id": task.agent_id,
                "request": task.request,
                "result": task.result,
            }
        )

    return task


def fail_task(
    agent_tasks: dict[str, AgentTask],
    task_id: str,
    result: Any = None,
) -> AgentTask:
    """
    Mark a task as failed and attach its result to its parent.
    """

    task = get_task(
        agent_tasks,
        task_id,
    )

    if task.status not in (
        AgentTaskStatus.ASSIGNED,
        AgentTaskStatus.RUNNING,
    ):
        raise ValueError(
            f"AgentTask '{task_id}' cannot be failed "
            f"from status {task.status.value}."
        )

    task.status = AgentTaskStatus.FAILED
    task.result = result

    parent = get_parent_task(
        agent_tasks,
        task_id,
    )

    if parent is not None:
        child_results = parent.metadata.setdefault(
            "child_results",
            [],
        )

        child_results.append(
            {
                "task_id": task.task_id,
                "agent_id": task.agent_id,
                "request": task.request,
                "result": task.result,
                "status": task.status.value,
            }
        )

    return task


def cancel_task(
    agent_tasks: dict[str, AgentTask],
    task_id: str,
) -> AgentTask:
    """
    Mark a task as cancelled.
    """

    task = get_task(
        agent_tasks,
        task_id,
    )

    if task.status in (
        AgentTaskStatus.COMPLETED,
        AgentTaskStatus.FAILED,
        AgentTaskStatus.CANCELLED,
    ):
        raise ValueError(
            f"AgentTask '{task_id}' cannot be cancelled "
            f"from status {task.status.value}."
        )

    task.status = AgentTaskStatus.CANCELLED

    return task
