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