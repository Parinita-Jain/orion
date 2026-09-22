import re

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


_REFERENCE_PATTERN = re.compile(
    r"#(\d+)\."
)


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

        agent = get_agent(
            task.agent_id
        )

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
        decision_context: str | None = None,
        allow_delegation: bool = True,
    ) -> str:

        agent = get_agent(
            task.agent_id
        )

        if agent is None:
            raise ValueError(
                f"Agent '{task.agent_id}' is not registered."
            )

        available_agents = {
            agent_id: definition
            for agent_id, definition in list_agents().items()
            if agent_id != task.agent_id
        }

        if available_agents:

            available_agent_ids = "\n".join(
                f"- {agent_id}"
                for agent_id in available_agents
            )

        else:

            available_agent_ids = "- none"

        delegation_rule = (
            "Delegation is allowed for this task."
            if allow_delegation
            else (
                "Delegation is NOT allowed for this task because "
                "the task has already started its own PlanSteps."
            )
        )

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

Current Task Context:
{decision_context or "No additional context is available."}

Available Agents:
{available_agent_ids}

{delegation_rule}

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
- Delegation is permitted only when the task has not started
  its own PlanSteps.

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
        decision_context: str | None = None,
        allow_delegation: bool = True,
    ) -> AgentDecision:

        prompt = self.build_decision_prompt(
            task,
            decision_context=decision_context,
            allow_delegation=allow_delegation,
        )

        structured_llm = llm.with_structured_output(
            AgentDecision
        )

        decision = structured_llm.invoke(
            prompt
        )

        if decision.action == AgentAction.DELEGATE:

            if not allow_delegation:
                raise ValueError(
                    f"AgentTask '{task.task_id}' cannot delegate "
                    "after its own PlanSteps have started."
                )

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

            if get_agent(
                decision.target_agent_id
            ) is None:
                raise ValueError(
                    f"Agent '{decision.target_agent_id}' "
                    "is not registered."
                )

            if (
                decision.target_agent_id
                == task.agent_id
            ):
                raise ValueError(
                    "An agent cannot delegate to itself."
                )

        return decision

    def plan_task(
        self,
        task: AgentTask,
        existing_steps: list[PlanStep] | None = None,
    ) -> list[PlanStep]:

        planning_request = self.build_planning_request(
            task
        )

        planned_steps = self.planning_service.plan(
            task.request,
            planning_context=planning_request,
        )

        if not existing_steps:
            return [
                replace(
                    step,
                    agent_task_id=task.task_id,
                )
                for step in planned_steps
            ]

        return self._remap_plan_steps(
            planned_steps,
            existing_steps,
            task.task_id,
        )

    def _remap_plan_steps(
        self,
        planned_steps: list[PlanStep],
        existing_steps: list[PlanStep],
        agent_task_id: str,
    ) -> list[PlanStep]:

        if not planned_steps:
            return []

        highest_id = max(
            (
                step.id
                for step in existing_steps
            ),
            default=0,
        )

        local_id_map = {
            step.id: highest_id + index + 1
            for index, step in enumerate(
                planned_steps
            )
        }

        def remap_reference(match):

            old_id = int(
                match.group(1)
            )

            if old_id in local_id_map:
                return (
                    f"#{local_id_map[old_id]}."
                )

            return match.group(0)

        remapped_steps = []

        for step in planned_steps:

            remapped_steps.append(
                replace(
                    step,
                    id=local_id_map[step.id],
                    depends_on=[
                        local_id_map.get(
                            dependency,
                            dependency,
                        )
                        for dependency in step.depends_on
                    ],
                    replaces=(
                        local_id_map.get(
                            step.replaces,
                            step.replaces,
                        )
                        if step.replaces is not None
                        else None
                    ),
                    tool_input=_REFERENCE_PATTERN.sub(
                        remap_reference,
                        step.tool_input,
                    ),
                    agent_task_id=agent_task_id,
                )
            )

        return remapped_steps