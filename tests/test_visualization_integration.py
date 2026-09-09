from models.execution_record import ExecutionRecord
from schemas import PlanStep
from shared_types.completion_status import CompletionStatus
from shared_types.step_status import StepStatus
from visualization import build_workflow_graph, render_mermaid


def test_workflow_state_to_mermaid():

    state = {
        "workflow_id": "integration-workflow",
        "completion_status": CompletionStatus.COMPLETE,
        "steps": [
            PlanStep(
                id=1,
                tool="rag",
                tool_input="research",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="#1.value",
                depends_on=[1],
            ),
            PlanStep(
                id=3,
                tool="direct",
                tool_input="independent task",
                depends_on=[],
            ),
            PlanStep(
                id=4,
                tool="replacement_tool",
                tool_input="fallback",
                depends_on=[],
                replaces=2,
            ),
        ],
        "tool_results": {
            1: {
                "status": StepStatus.SUCCESS,
                "error": None,
            },
            2: {
                "status": StepStatus.SUPERSEDED,
                "error": "Original execution failed",
            },
            3: {
                "status": StepStatus.SUCCESS,
                "error": None,
            },
            4: {
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
                end_time=3,
                duration=2,
            ),
            ExecutionRecord(
                step_id=2,
                tool="calculator",
                success=False,
                retries=2,
                start_time=3,
                end_time=6,
                duration=3,
                error="Original execution failed",
            ),
            ExecutionRecord(
                step_id=3,
                tool="direct",
                success=True,
                retries=0,
                start_time=3,
                end_time=4,
                duration=1,
            ),
            ExecutionRecord(
                step_id=4,
                tool="replacement_tool",
                success=True,
                retries=0,
                start_time=6,
                end_time=7,
                duration=1,
            ),
        ],
    }

    graph = build_workflow_graph(state)

    mermaid = render_mermaid(graph)

    assert graph.workflow_id == "integration-workflow"
    assert graph.completion_status == CompletionStatus.COMPLETE

    assert len(graph.nodes) == 4
    assert len(graph.edges) == 2

    # Dependency: Step 1 -> Step 2
    assert any(
        edge.source == 1
        and edge.target == 2
        for edge in graph.edges
    )

    # Replacement: Step 2 -> Step 4
    assert any(
        edge.source == 2
        and edge.target == 4
        for edge in graph.edges
    )

    # Runtime information
    step_2 = next(node for node in graph.nodes if node.id == 2)

    assert step_2.status == StepStatus.SUPERSEDED
    assert step_2.retries == 2
    assert step_2.duration == 3

    step_4 = next(node for node in graph.nodes if node.id == 4)

    assert step_4.status == StepStatus.SUCCESS
    assert step_4.replaces == 2

    # Renderer output
    assert "graph TD" in mermaid
    assert "S1 --> S2" in mermaid
    assert "S2 -. replaces .-> S4" in mermaid
    assert "SUPERSEDED" in mermaid
    assert "SUCCESS" in mermaid
    assert "Retries: 2" in mermaid