from config import logger
from errors import OrionError

from .llm import get_structured_llm
from .repair import repair_plan

from .service import (
    MAX_REPAIR_ATTEMPTS,
    PlanningService,
)


def planner_node(state):

    question = state["messages"][-1].content

    logger.info(
        "Planner node received workflow request"
    )

    current_task_id = state.get(
        "current_agent_task_id"
    )

    agent_tasks = state.get(
        "agent_tasks",
        {}
    )

    if (
        current_task_id is not None
        and current_task_id in agent_tasks
    ):

        from agents.runtime import AgentRuntime

        task = agent_tasks[
            current_task_id
        ]

        runtime = AgentRuntime()

        try:

            steps = runtime.plan_task(
                task,
                existing_steps=state.get("steps", []),
            )

        except OrionError as e:

            return {
                "steps": [],
                "error": e,
            }

        return {
            "steps": (
                state.get(
                    "steps",
                    [],
                )
                + steps
            ),
            "error": None,
        }

    planning_service = PlanningService(
        get_structured_llm=get_structured_llm,
        repair_plan=repair_plan,
    )

    try:

        steps = planning_service.plan(
            question
        )

    except OrionError as e:

        return {
            "steps": [],
            "error": e,
        }

    return {
        "steps": steps,
        "error": None,
    }