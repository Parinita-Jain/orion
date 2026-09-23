from models.execution_record import ExecutionRecord
from state import AgentState
from visualization.model import (
    AgentEdge,
    AgentEdgeType,
    AgentTaskNode,
    EdgeType,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)


def build_workflow_graph(state: AgentState) -> WorkflowGraph:
    tool_results = state.get("tool_results", {})
    execution_records = state.get("execution_records", [])

    agent_tasks = state.get("agent_tasks", {})
    agent_messages = state.get("agent_messages", [])

    records_by_step: dict[int, list[ExecutionRecord]] = {}

    for record in execution_records:
        records_by_step.setdefault(record.step_id, []).append(record)

    # ------------------------------------------------------------------
    # AgentTask visualization layer
    # ------------------------------------------------------------------

    message_counts: dict[str, int] = {}

    for message in agent_messages:
        if message.task_id is not None:
            message_counts[message.task_id] = (
                message_counts.get(message.task_id, 0) + 1
            )

    agent_task_nodes = []

    for task in agent_tasks.values():
        task_error = task.metadata.get("error")

        agent_task_nodes.append(
            AgentTaskNode(
                task_id=task.task_id,
                parent_task_id=task.parent_task_id,
                agent_id=task.agent_id,
                request=task.request,
                status=task.status,
                result=task.result,
                error=task_error,
                message_count=message_counts.get(
                    task.task_id,
                    0,
                ),
            )
        )

    agent_edges = []

    for task in agent_tasks.values():
        if task.parent_task_id is not None:
            agent_edges.append(
                AgentEdge(
                    source=task.parent_task_id,
                    target=task.task_id,
                    type=AgentEdgeType.DELEGATION,
                )
            )

    # ------------------------------------------------------------------
    # PlanStep visualization layer
    # ------------------------------------------------------------------

    nodes = []

    for step in state.get("steps", []):
        result = tool_results.get(step.id, {})
        records = records_by_step.get(step.id, [])

        retries = sum(record.retries for record in records)
        duration = sum(record.duration for record in records)

        agent_task_id = getattr(
            step,
            "agent_task_id",
            None,
        )

        agent_id = None

        if (
            agent_task_id is not None
            and agent_task_id in agent_tasks
        ):
            agent_id = agent_tasks[agent_task_id].agent_id

        nodes.append(
            WorkflowNode(
                id=step.id,
                tool=step.tool,
                status=result.get("status"),
                retries=retries,
                duration=duration,
                error=result.get("error"),
                condition=step.condition,
                approval_required=(
                    step.approval is not None
                    and step.approval.required
                ),
                replaces=step.replaces,
                agent_task_id=agent_task_id,
                agent_id=agent_id,
            )
        )

    edges = []

    for step in state.get("steps", []):
        for dependency in step.depends_on:
            edges.append(
                WorkflowEdge(
                    source=dependency,
                    target=step.id,
                    type=EdgeType.DEPENDENCY,
                )
            )

        if step.replaces is not None:
            edges.append(
                WorkflowEdge(
                    source=step.replaces,
                    target=step.id,
                    type=EdgeType.REPLACEMENT,
                )
            )

    # ------------------------------------------------------------------
    # AgentTask -> PlanStep ownership relationships
    # ------------------------------------------------------------------

    for step in state.get("steps", []):
        agent_task_id = getattr(
            step,
            "agent_task_id",
            None,
        )

        if agent_task_id is not None:
            agent_edges.append(
                AgentEdge(
                    source=agent_task_id,
                    target=f"S{step.id}",
                    type=AgentEdgeType.OWNERSHIP,
                )
            )

    return WorkflowGraph(
        workflow_id=state.get("workflow_id", ""),
        completion_status=state.get("completion_status"),
        agent_tasks=agent_task_nodes,
        nodes=nodes,
        edges=edges,
        agent_edges=agent_edges,
    )