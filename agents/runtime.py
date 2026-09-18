from dataclasses import replace

from agents.registry import get_agent
from agents.task import AgentTask
from models.plan import PlanStep

from planner.service import PlanningService


class AgentRuntime:
    """
    Runtime boundary for processing an AgentTask.
    """

    def __init__(
        self,
        planning_service: PlanningService | None = None,
    ):
        self.planning_service = (
            planning_service
            if planning_service is not None
            else PlanningService()
        )

    def build_planning_request(
        self,
        task: AgentTask,
    ) -> str:

        agent = get_agent(task.agent_id)

        if agent is None:
            raise ValueError(
                f"Agent '{task.agent_id}' is not registered."
            )

        return (
            f"Agent: {agent.name}\n"
            f"Agent Role: {agent.role}\n"
            f"Agent Instructions:\n"
            f"{agent.instructions}\n\n"
            f"Assigned Task:\n"
            f"{task.request}"
        )

    def plan_task(
        self,
        task: AgentTask,
    ) -> list[PlanStep]:

        planning_request = self.build_planning_request(
            task
        )

        planned_steps = self.planning_service.plan(
            task.request,
            planning_context=planning_request,
        )

        return [
            replace(
                step,
                agent_task_id=task.task_id,
            )
            for step in planned_steps
        ]