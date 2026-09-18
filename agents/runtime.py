from dataclasses import replace

from shared import llm

from agents.decision import (
    AgentAction,
    AgentDecision,
)
from agents.registry import (
    get_agent,
    list_agents,
)
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

    def build_decision_prompt(
        self,
        task: AgentTask,
    ) -> str:

        agent = get_agent(task.agent_id)

        if agent is None:
            raise ValueError(
                f"Agent '{task.agent_id}' is not registered."
            )

        available_agents = list_agents()

        if available_agents:
            available_agent_ids = "\n".join(
                f"- {agent_id}"
                for agent_id in available_agents
            )
        else:
            available_agent_ids = "- none"

        return f"""
You are an Orion agent deciding what to do next.

Agent:
{agent.name}

Role:
{agent.role}

Instructions:
{agent.instructions}

Assigned Task:
{task.request}

Available Agents:
{available_agent_ids}

Choose exactly one action:

1. PLAN

Use PLAN when the current agent should solve the assigned task
using Orion's normal planning and execution flow.

2. DELEGATE

Use DELEGATE when another registered agent should perform part
of the work.

When choosing DELEGATE:

- target_agent_id must be the ID of one of the available agents.
- request must contain the specific work to be delegated.
- Do not invent agent IDs.

3. COMPLETE

Use COMPLETE when the assigned task has been fulfilled.

When choosing COMPLETE, provide the result when one is available.

Do not execute tools yourself.
Do not create PlanSteps.
Only decide what the agent should do next.
"""

    def decide_task(
        self,
        task: AgentTask,
    ) -> AgentDecision:

        prompt = self.build_decision_prompt(task)

        structured_llm = llm.with_structured_output(
            AgentDecision
        )

        decision = structured_llm.invoke(prompt)

        if decision.action == AgentAction.DELEGATE:

            if not decision.target_agent_id:
                raise ValueError(
                    "Delegation decision must specify "
                    "target_agent_id."
                )

            if not decision.request:
                raise ValueError(
                    "Delegation decision must specify "
                    "a non-empty request."
                )

            if get_agent(decision.target_agent_id) is None:
                raise ValueError(
                    f"Agent '{decision.target_agent_id}' "
                    "is not registered."
                )

        return decision

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