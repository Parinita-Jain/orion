from visualization.mermaid import render_mermaid
from visualization.model import (
    EdgeType,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)
from agents.task import AgentTaskStatus
from visualization.model import (
    AgentEdge,
    AgentEdgeType,
    AgentTaskNode,
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

def test_render_mermaid_agent_tasks():

    graph = WorkflowGraph(
        workflow_id="agent-workflow",
        agent_tasks=[
            AgentTaskNode(
                task_id="T1",
                parent_task_id=None,
                agent_id="supervisor",
                request="Delegate research.",
                status=AgentTaskStatus.COMPLETED,
            ),
            AgentTaskNode(
                task_id="T2",
                parent_task_id="T1",
                agent_id="research",
                request="Research the topic.",
                status=AgentTaskStatus.RUNNING,
                message_count=2,
            ),
        ],
    )

    result = render_mermaid(graph)

    assert 'T1["T1: supervisor<br/>COMPLETED' in result
    assert 'T2["T2: research<br/>RUNNING' in result
    assert "Request: Delegate research." in result
    assert "Messages: 2" in result
    assert "class T1 agent_status_completed" in result
    assert "class T2 agent_status_running" in result


def test_render_mermaid_agent_relationships():

    graph = WorkflowGraph(
        workflow_id="agent-workflow",
        agent_tasks=[
            AgentTaskNode(
                task_id="T1",
                parent_task_id=None,
                agent_id="supervisor",
                request="Delegate.",
                status=AgentTaskStatus.COMPLETED,
            ),
            AgentTaskNode(
                task_id="T2",
                parent_task_id="T1",
                agent_id="research",
                request="Research.",
                status=AgentTaskStatus.COMPLETED,
            ),
        ],
        agent_edges=[
            AgentEdge(
                source="T1",
                target="T2",
                type=AgentEdgeType.DELEGATION,
            ),
            AgentEdge(
                source="T2",
                target="S1",
                type=AgentEdgeType.OWNERSHIP,
            ),
        ],
    )

    result = render_mermaid(graph)

    assert "T1 -->|delegates| T2" in result
    assert "T2 -. owns .-> S1" in result


def test_render_mermaid_agent_step_association():

    graph = WorkflowGraph(
        workflow_id="agent-workflow",
        agent_tasks=[
            AgentTaskNode(
                task_id="T2",
                parent_task_id="T1",
                agent_id="research",
                request="Research.",
                status=AgentTaskStatus.COMPLETED,
            ),
        ],
        nodes=[
            WorkflowNode(
                id=1,
                tool="rag",
                status=StepStatus.SUCCESS,
                agent_task_id="T2",
                agent_id="research",
            ),
        ],
    )

    result = render_mermaid(graph)

    assert "Task: T2" in result
    assert "Agent: research" in result