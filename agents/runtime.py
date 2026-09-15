from dataclasses import replace
from typing import Callable

from agents.registry import get_agent
from agents.task import AgentTask
from models.plan import PlanStep


class AgentRuntime:
    """
    Runtime boundary for processing an AgentTask.

    This first version deliberately does not execute PlanSteps and does not
    invoke the LangGraph workflow directly.

    It resolves the target agent, prepares agent-specific planning context,
    invokes an injected planning function, and associates the resulting
    runtime PlanSteps with the AgentTask.
    """

    def build_planning_request(self, task: AgentTask) -> str:
        """
        Build the planning request supplied to the planner.

        Agent identity, role, instructions, and task request are kept together
        so the planner can specialize its planning behavior for the agent.
        """

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
        planner: Callable[[str], list[PlanStep]],
    ) -> list[PlanStep]:
        """
        Generate runtime PlanSteps for an AgentTask.

        The planner is injected rather than imported directly. This keeps the
        agent runtime independent of the current LangGraph planner node and
        allows the planner integration to be introduced separately.
        """

        planning_request = self.build_planning_request(task)

        planned_steps = planner(planning_request)

        if planned_steps is None:
            raise ValueError(
                "Planner returned no steps."
            )

        if not isinstance(planned_steps, list):
            raise TypeError(
                "Planner must return a list of PlanStep objects."
            )

        runtime_steps = []

        for step in planned_steps:

            if not isinstance(step, PlanStep):
                raise TypeError(
                    "Planner returned a non-PlanStep object."
                )

            runtime_steps.append(
                replace(
                    step,
                    agent_task_id=task.task_id,
                )
            )

        return runtime_steps