from agents.message import AgentMessage
from agents.task import (
    AgentTask,
    AgentTaskStatus,
)
from models.execution_record import ExecutionRecord
from models.plan import PlanStep as RuntimePlanStep
from schemas import PlanStep
from shared_types.completion_status import CompletionStatus
from shared_types.step_status import StepStatus
from visualization.builder import build_workflow_graph
from visualization.model import AgentEdgeType


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

from agents.task import (
    AgentTask,
    AgentTaskStatus,
)
from agents.message import AgentMessage


def test_builder_creates_agent_task_nodes():

    state = {
        "workflow_id": "agent-workflow",
        "agent_tasks": {
            "T1": AgentTask(
                task_id="T1",
                parent_task_id=None,
                agent_id="supervisor",
                request="Research and calculate.",
                status=AgentTaskStatus.COMPLETED,
                result="Completed",
            ),
            "T2": AgentTask(
                task_id="T2",
                parent_task_id="T1",
                agent_id="research",
                request="Research the topic.",
                status=AgentTaskStatus.COMPLETED,
                result="Research result",
            ),
        },
        "agent_messages": [
            AgentMessage(
                message_id="M1",
                sender="supervisor",
                recipient="research",
                content="Please research this.",
                task_id="T2",
            ),
            AgentMessage(
                message_id="M2",
                sender="research",
                recipient="supervisor",
                content="Research completed.",
                task_id="T2",
            ),
        ],
        "steps": [],
        "tool_results": {},
        "execution_records": [],
    }

    graph = build_workflow_graph(state)

    assert len(graph.agent_tasks) == 2

    supervisor = graph.agent_tasks[0]
    research = graph.agent_tasks[1]

    assert supervisor.task_id == "T1"
    assert supervisor.parent_task_id is None
    assert supervisor.agent_id == "supervisor"

    assert research.task_id == "T2"
    assert research.parent_task_id == "T1"
    assert research.agent_id == "research"
    assert research.message_count == 2
    assert research.result == "Research result"


def test_builder_creates_delegation_edges():

    state = {
        "workflow_id": "delegation-workflow",
        "agent_tasks": {
            "T1": AgentTask(
                task_id="T1",
                parent_task_id=None,
                agent_id="supervisor",
                request="Delegate research.",
                status=AgentTaskStatus.COMPLETED,
            ),
            "T2": AgentTask(
                task_id="T2",
                parent_task_id="T1",
                agent_id="research",
                request="Research this.",
                status=AgentTaskStatus.COMPLETED,
            ),
            "T3": AgentTask(
                task_id="T3",
                parent_task_id="T2",
                agent_id="calculator",
                request="Calculate this.",
                status=AgentTaskStatus.COMPLETED,
            ),
        },
        "agent_messages": [],
        "steps": [],
        "tool_results": {},
        "execution_records": [],
    }

    graph = build_workflow_graph(state)

    delegation_edges = [
        edge
        for edge in graph.agent_edges
        if edge.type == AgentEdgeType.DELEGATION
    ]

    assert len(delegation_edges) == 2

    assert delegation_edges[0].source == "T1"
    assert delegation_edges[0].target == "T2"

    assert delegation_edges[1].source == "T2"
    assert delegation_edges[1].target == "T3"


def test_builder_creates_step_ownership_edges():

    state = {
        "workflow_id": "ownership-workflow",
        "agent_tasks": {
            "T1": AgentTask(
                task_id="T1",
                parent_task_id=None,
                agent_id="supervisor",
                request="Do work.",
                status=AgentTaskStatus.RUNNING,
            ),
            "T2": AgentTask(
                task_id="T2",
                parent_task_id="T1",
                agent_id="research",
                request="Research.",
                status=AgentTaskStatus.RUNNING,
            ),
        },
        "agent_messages": [],
        "steps": [
            RuntimePlanStep(
                id=1,
                tool="rag",
                tool_input="research",
                depends_on=[],
                agent_task_id="T2",
            ),
            RuntimePlanStep(
                id=2,
                tool="calculator",
                tool_input="#1.value",
                depends_on=[1],
                agent_task_id="T2",
            ),
        ],
        "tool_results": {},
        "execution_records": [],
    }

    graph = build_workflow_graph(state)

    ownership_edges = [
        edge
        for edge in graph.agent_edges
        if edge.type == AgentEdgeType.OWNERSHIP
    ]

    assert len(ownership_edges) == 2

    assert ownership_edges[0].source == "T2"
    assert ownership_edges[0].target == "S1"

    assert ownership_edges[1].source == "T2"
    assert ownership_edges[1].target == "S2"

    assert graph.nodes[0].agent_task_id == "T2"
    assert graph.nodes[0].agent_id == "research"

    assert graph.nodes[1].agent_task_id == "T2"
    assert graph.nodes[1].agent_id == "research"