from models.execution_record import ExecutionRecord
from state import AgentState
from visualization.model import (
    EdgeType,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)


def build_workflow_graph(state: AgentState) -> WorkflowGraph:
    tool_results = state.get("tool_results", {})
    execution_records = state.get("execution_records", [])

    records_by_step: dict[int, list[ExecutionRecord]] = {}

    for record in execution_records:
        records_by_step.setdefault(record.step_id, []).append(record)

    nodes = []

    for step in state.get("steps", []):
        result = tool_results.get(step.id, {})
        records = records_by_step.get(step.id, [])

        retries = sum(record.retries for record in records)
        duration = sum(record.duration for record in records)

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

    return WorkflowGraph(
        workflow_id=state.get("workflow_id", ""),
        completion_status=state.get("completion_status"),
        nodes=nodes,
        edges=edges,
    )
