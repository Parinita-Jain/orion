from visualization.builder import build_workflow_graph
from shared_types.completion_status import CompletionStatus
from shared_types.step_status import StepStatus
from models.execution_record import ExecutionRecord
from schemas import PlanStep


def test_builder_creates_nodes_and_dependency_edges():

    state = {
        "workflow_id": "workflow-1",
        "completion_status": CompletionStatus.COMPLETE,
        "steps": [
            PlanStep(
                id=1,
                tool="rag",
                tool_input="question",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="#1.value",
                depends_on=[1],
            ),
        ],
        "tool_results": {
            1: {
                "status": StepStatus.SUCCESS,
                "error": None,
            },
            2: {
                "status": StepStatus.SUCCESS,
                "error": None,
            },
        },
        "execution_records": [
            ExecutionRecord(
                step_id=1,
                tool="rag",
                success=True,
                retries=1,
                start_time=1,
                end_time=2,
                duration=1,
            ),
            ExecutionRecord(
                step_id=2,
                tool="calculator",
                success=True,
                retries=0,
                start_time=2,
                end_time=3,
                duration=1,
            ),
        ],
    }

    graph = build_workflow_graph(state)

    assert graph.workflow_id == "workflow-1"
    assert graph.completion_status == CompletionStatus.COMPLETE

    assert len(graph.nodes) == 2

    assert graph.nodes[0].id == 1
    assert graph.nodes[0].status == StepStatus.SUCCESS
    assert graph.nodes[0].retries == 1
    assert graph.nodes[0].duration == 1

    assert graph.nodes[1].id == 2
    assert graph.nodes[1].status == StepStatus.SUCCESS

    assert len(graph.edges) == 1

    edge = graph.edges[0]

    assert edge.source == 1
    assert edge.target == 2


def test_builder_creates_replacement_edge():

    state = {
        "workflow_id": "workflow-2",
        "steps": [
            PlanStep(
                id=1,
                tool="bad_tool",
                tool_input="input",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="replacement_tool",
                tool_input="input",
                depends_on=[],
                replaces=1,
            ),
        ],
        "tool_results": {
            1: {
                "status": StepStatus.SUPERSEDED,
                "error": "Original failed",
            },
            2: {
                "status": StepStatus.SUCCESS,
                "error": None,
            },
        },
        "execution_records": [],
    }

    graph = build_workflow_graph(state)

    assert len(graph.nodes) == 2

    assert graph.nodes[0].status == StepStatus.SUPERSEDED
    assert graph.nodes[1].status == StepStatus.SUCCESS
    assert graph.nodes[1].replaces == 1

    assert len(graph.edges) == 1

    edge = graph.edges[0]

    assert edge.source == 1
    assert edge.target == 2


def test_builder_handles_pending_step_without_execution_history():

    state = {
        "workflow_id": "workflow-3",
        "steps": [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+2",
                depends_on=[],
            )
        ],
        "tool_results": {},
        "execution_records": [],
    }

    graph = build_workflow_graph(state)

    node = graph.nodes[0]

    assert node.status is None
    assert node.retries == 0
    assert node.duration == 0
    assert node.error is None