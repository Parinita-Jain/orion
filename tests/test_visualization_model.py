from visualization.model import (
    EdgeType,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)
from shared_types.completion_status import CompletionStatus
from shared_types.step_status import StepStatus


def test_workflow_node_defaults():

    node = WorkflowNode(
        id=1,
        tool="calculator",
    )

    assert node.id == 1
    assert node.tool == "calculator"
    assert node.status is None
    assert node.retries == 0
    assert node.duration == 0.0
    assert node.error is None
    assert node.condition is None
    assert node.approval_required is False
    assert node.replaces is None


def test_workflow_node_runtime_information():

    node = WorkflowNode(
        id=2,
        tool="rag",
        status=StepStatus.FAILED,
        retries=2,
        duration=1.5,
        error="Tool failed",
        condition="step_1.success",
        approval_required=True,
        replaces=1,
    )

    assert node.status == StepStatus.FAILED
    assert node.retries == 2
    assert node.duration == 1.5
    assert node.error == "Tool failed"
    assert node.condition == "step_1.success"
    assert node.approval_required is True
    assert node.replaces == 1


def test_workflow_edges():

    dependency = WorkflowEdge(
        source=1,
        target=2,
        type=EdgeType.DEPENDENCY,
    )

    replacement = WorkflowEdge(
        source=2,
        target=3,
        type=EdgeType.REPLACEMENT,
    )

    assert dependency.source == 1
    assert dependency.target == 2
    assert dependency.type == EdgeType.DEPENDENCY

    assert replacement.source == 2
    assert replacement.target == 3
    assert replacement.type == EdgeType.REPLACEMENT


def test_workflow_graph():

    graph = WorkflowGraph(
        workflow_id="test-workflow",
        completion_status=CompletionStatus.COMPLETE,
        nodes=[
            WorkflowNode(
                id=1,
                tool="calculator",
                status=StepStatus.SUCCESS,
            )
        ],
        edges=[
            WorkflowEdge(
                source=1,
                target=2,
                type=EdgeType.DEPENDENCY,
            )
        ],
    )

    assert graph.workflow_id == "test-workflow"
    assert graph.completion_status == CompletionStatus.COMPLETE
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 1