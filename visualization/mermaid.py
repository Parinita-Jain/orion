from visualization.model import (
    AgentEdgeType,
    EdgeType,
    WorkflowGraph,
)


def _escape_label(value: str) -> str:
    """Escape characters that can interfere with Mermaid labels."""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', "'")
        .replace("\n", "<br/>")
    )


def _format_status(status) -> str:
    if status is None:
        return "PENDING"

    return str(
        status.value
        if hasattr(status, "value")
        else status
    ).upper()


def _status_class(status) -> str:
    return f"status_{_format_status(status).lower()}"


def _agent_status_class(status) -> str:
    return f"agent_status_{_format_status(status).lower()}"


def render_mermaid(graph: WorkflowGraph) -> str:
    """Render a WorkflowGraph as a Mermaid flowchart."""

    lines = [
        "graph TD",
        "",
        "    classDef status_pending fill:#f5f5f5,stroke:#999",
        "    classDef status_running fill:#fff3cd,stroke:#d39e00",
        "    classDef status_success fill:#d4edda,stroke:#28a745",
        "    classDef status_failed fill:#f8d7da,stroke:#dc3545",
        "    classDef status_superseded fill:#e2e3e5,stroke:#6c757d,stroke-dasharray: 5 5",
        "",
        "    classDef agent_status_created fill:#f5f5f5,stroke:#999",
        "    classDef agent_status_assigned fill:#e8e8e8,stroke:#777",
        "    classDef agent_status_running fill:#fff3cd,stroke:#d39e00",
        "    classDef agent_status_completed fill:#d4edda,stroke:#28a745",
        "    classDef agent_status_failed fill:#f8d7da,stroke:#dc3545",
        "    classDef agent_status_cancelled fill:#e2e3e5,stroke:#6c757d,stroke-dasharray: 5 5",
        "",
    ]

    # ------------------------------------------------------------------
    # AgentTask nodes
    # ------------------------------------------------------------------

    for task in graph.agent_tasks:
        status = _format_status(task.status)

        label_parts = [
            f"{_escape_label(task.task_id)}: "
            f"{_escape_label(task.agent_id)}",
            status,
        ]

        if task.request:
            label_parts.append(
                f"Request: {_escape_label(task.request)}"
            )

        if task.message_count:
            label_parts.append(
                f"Messages: {task.message_count}"
            )

        if task.result is not None:
            label_parts.append(
                f"Result: {_escape_label(task.result)}"
            )

        if task.error:
            label_parts.append(
                f"Error: {_escape_label(task.error)}"
            )

        label = "<br/>".join(label_parts)

        lines.append(
            f'    {task.task_id}["{label}"]'
        )

        lines.append(
            f"    class {task.task_id} "
            f"{_agent_status_class(task.status)}"
        )

    # ------------------------------------------------------------------
    # PlanStep nodes
    # ------------------------------------------------------------------

    for node in graph.nodes:
        status = _format_status(node.status)

        label_parts = [
            f"{node.id}: {_escape_label(node.tool)}",
            status,
        ]

        if node.agent_task_id:
            label_parts.append(
                f"Task: {_escape_label(node.agent_task_id)}"
            )

        if node.agent_id:
            label_parts.append(
                f"Agent: {_escape_label(node.agent_id)}"
            )

        if node.retries:
            label_parts.append(
                f"Retries: {node.retries}"
            )

        if node.duration:
            label_parts.append(
                f"Duration: {node.duration:.3f}s"
            )

        if node.error:
            label_parts.append(
                f"Error: {_escape_label(node.error)}"
            )

        label = "<br/>".join(label_parts)

        lines.append(
            f'    S{node.id}["{label}"]'
        )

        lines.append(
            f"    class S{node.id} "
            f"{_status_class(node.status)}"
        )

    # ------------------------------------------------------------------
    # AgentTask relationships
    # ------------------------------------------------------------------

    for edge in graph.agent_edges:

        if edge.type == AgentEdgeType.DELEGATION:
            lines.append(
                f"    {edge.source} -->|delegates| {edge.target}"
            )

        elif edge.type == AgentEdgeType.OWNERSHIP:
            lines.append(
                f"    {edge.source} -. owns .-> {edge.target}"
            )

    # ------------------------------------------------------------------
    # PlanStep relationships
    # ------------------------------------------------------------------

    for edge in graph.edges:

        if edge.type == EdgeType.DEPENDENCY:
            lines.append(
                f"    S{edge.source} --> S{edge.target}"
            )

        elif edge.type == EdgeType.REPLACEMENT:
            lines.append(
                f"    S{edge.source} -. replaces .-> S{edge.target}"
            )

    return "\n".join(lines)