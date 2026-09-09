from visualization.mermaid import render_mermaid
from visualization.model import (
    EdgeType,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)
from shared_types.step_status import StepStatus


def test_render_mermaid_basic_graph():

    graph = WorkflowGraph(
        workflow_id="test",
        nodes=[
            WorkflowNode(
                id=1,
                tool="rag",
                status=StepStatus.SUCCESS,
            ),
            WorkflowNode(
                id=2,
                tool="calculator",
                status=StepStatus.SUCCESS,
            ),
        ],
        edges=[
            WorkflowEdge(
                source=1,
                target=2,
                type=EdgeType.DEPENDENCY,
            )
        ],
    )

    result = render_mermaid(graph)

    assert result.startswith("graph TD")
    assert 'S1["1: rag<br/>SUCCESS"]' in result
    assert 'S2["2: calculator<br/>SUCCESS"]' in result
    assert "S1 --> S2" in result
    assert "classDef status_success" in result
    assert "class S1 status_success" in result
    assert "class S2 status_success" in result


def test_render_mermaid_replacement_edge():

    graph = WorkflowGraph(
        workflow_id="test",
        nodes=[
            WorkflowNode(
                id=1,
                tool="old_tool",
                status=StepStatus.SUPERSEDED,
            ),
            WorkflowNode(
                id=2,
                tool="new_tool",
                status=StepStatus.SUCCESS,
                replaces=1,
            ),
        ],
        edges=[
            WorkflowEdge(
                source=1,
                target=2,
                type=EdgeType.REPLACEMENT,
            )
        ],
    )

    result = render_mermaid(graph)

    assert "S1 -. replaces .-> S2" in result
    assert "SUPERSEDED" in result
    assert "classDef status_superseded" in result
    assert "class S1 status_superseded" in result
    assert "class S2 status_success" in result


def test_render_mermaid_pending_step():

    graph = WorkflowGraph(
        workflow_id="test",
        nodes=[
            WorkflowNode(
                id=1,
                tool="calculator",
            )
        ],
    )

    result = render_mermaid(graph)

    assert "PENDING" in result
    assert "classDef status_pending" in result
    assert "class S1 status_pending" in result


def test_render_mermaid_execution_metadata():

    graph = WorkflowGraph(
        workflow_id="test",
        nodes=[
            WorkflowNode(
                id=1,
                tool="calculator",
                status=StepStatus.FAILED,
                retries=2,
                duration=1.23456,
                error='Tool "calculator" failed',
            )
        ],
    )

    result = render_mermaid(graph)

    assert "Retries: 2" in result
    assert "Duration: 1.235s" in result
    assert "Error: Tool 'calculator' failed" in result
    assert "classDef status_failed" in result
    assert "class S1 status_failed" in result


def test_render_mermaid_escapes_multiline_labels():

    graph = WorkflowGraph(
        workflow_id="test",
        nodes=[
            WorkflowNode(
                id=1,
                tool='tool "quoted"',
                status=StepStatus.FAILED,
                error="first line\nsecond line",
            )
        ],
    )

    result = render_mermaid(graph)

    assert "tool 'quoted'" in result
    assert "first line<br/>second line" in result
