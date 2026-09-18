from agents.models import AgentDefinition
from agents.registry import (
    get_agent,
    register_agent,
)
from agents.task import (
    AgentTask,
    AgentTaskStatus,
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

    agent = get_agent(SUPERVISOR_AGENT.id)

    if agent is None:
        register_agent(SUPERVISOR_AGENT)
        agent = SUPERVISOR_AGENT

    return agent


def _next_task_id(agent_tasks):
    """
    Generate the next workflow-local task ID.
    """

    number = 1

    while f"T{number}" in agent_tasks:
        number += 1

    return f"T{number}"


def _find_root_task(agent_tasks):

    for task in agent_tasks.values():

        if task.parent_task_id is None:
            return task

    return None


def agent_node(state):

    print("\n===== AGENT NODE =====")

    agent_tasks = dict(
        state.get("agent_tasks", {})
    )

    agent_messages = list(
        state.get("agent_messages", [])
    )

    current_task_id = state.get(
        "current_agent_task_id"
    )

    task = None

    if current_task_id is not None:
        task = agent_tasks.get(current_task_id)

    if task is None:
        task = _find_root_task(agent_tasks)

    if task is None:

        messages = state.get("messages", [])

        if not messages:
            raise ValueError(
                "Cannot create supervisor task without a user message."
            )

        request = messages[-1].content

        get_supervisor_agent()

        task_id = _next_task_id(agent_tasks)

        task = AgentTask(
            task_id=task_id,
            parent_task_id=None,
            agent_id="supervisor",
            request=request,
            status=AgentTaskStatus.ASSIGNED,
        )

        agent_tasks[task_id] = task

    task.status = AgentTaskStatus.RUNNING

    return {
        "agent_tasks": agent_tasks,
        "agent_messages": agent_messages,
        "current_agent_task_id": task.task_id,
        "iteration": state.get("iteration", 0),
    }