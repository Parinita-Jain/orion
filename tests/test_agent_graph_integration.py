from unittest.mock import patch

from langchain_core.messages import HumanMessage

from agents.decision import (
    AgentAction,
    AgentDecision,
)

from agents.registry import (
    clear_registry,
    register_agent,
)

from workflow.graph import app

from agents.models import AgentDefinition

from agents.task import AgentTaskStatus

from runtime.runtime_config import RuntimeConfig
from runtime.event import WorkflowEvent
from runtime.event_bus import EventBus

from shared_types.workflow_event_type import WorkflowEventType

from workflow.graph import app

import planner.node as planner_node_module

def setup_function():
    clear_registry()

    register_agent(
        AgentDefinition(
            id="supervisor",
            name="Supervisor Agent",
            role="supervisor",
            instructions="Coordinate work.",
        )
    )

    register_agent(
        AgentDefinition(
            id="research",
            name="Research Agent",
            role="research",
            instructions="Perform research.",
        )
    )


def teardown_function():
    clear_registry()


class FakeListener:

    def __init__(self):
        self.events = []

    def __call__(self, event):
        self.events.append(event)


def test_compiled_graph_delegates_and_returns_to_parent():

    listener = FakeListener()

    event_bus = EventBus()
    event_bus.subscribe(listener)

    decisions = [
        AgentDecision(
            action=AgentAction.DELEGATE,
            target_agent_id="research",
            request="Research the assigned subject.",
        ),
        AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Research complete."
            },
        ),
        AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Final answer."
            },
        ),
    ]

    with patch(
        "agents.runtime.AgentRuntime.decide_task",
        side_effect=decisions,
    ), patch(
        "langchain_core.language_models.BaseChatModel.invoke"
    ) as mock_llm:

        mock_llm.return_value.content = (
            "Final synthesized response."
        )

        state = {
            "workflow_id": "multi-agent-integration-test",
            "messages": [
                HumanMessage(
                    content="Research the assigned subject."
                )
            ],
            "agent_tasks": {},
            "agent_messages": [],
            "current_agent_task_id": None,
            "steps": [],
            "tool_results": {},
            "execution_records": [],
            "context": {},
            "output": {},
            "runtime_config": RuntimeConfig(),
            "event_bus": event_bus,
            "error": None,
            "done": False,
        }

        result = app.invoke(state)

    assert result["error"] is None

    assert "T1" in result["agent_tasks"]
    assert "T2" in result["agent_tasks"]

    root = result["agent_tasks"]["T1"]
    child = result["agent_tasks"]["T2"]

    assert root.agent_id == "supervisor"
    assert root.parent_task_id is None
    assert root.status == AgentTaskStatus.COMPLETED

    assert child.agent_id == "research"
    assert child.parent_task_id == "T1"
    assert child.status == AgentTaskStatus.COMPLETED

    assert child.result == {
        "answer": "Research complete."
    }

    assert root.metadata["child_results"] == [
        {
            "task_id": "T2",
            "agent_id": "research",
            "request": "Research the assigned subject.",
            "result": {
                "answer": "Research complete."
            },
        }
    ]

    assert len(result["agent_messages"]) == 2

    delegation_message = result["agent_messages"][0]

    assert delegation_message.sender == "supervisor"
    assert delegation_message.recipient == "research"
    assert delegation_message.task_id == "T2"
    assert delegation_message.content == (
        "Research the assigned subject."
    )

    completion_message = result["agent_messages"][1]

    assert completion_message.sender == "research"
    assert completion_message.recipient == "supervisor"
    assert completion_message.task_id == "T2"
    assert completion_message.content == {
        "answer": "Research complete."
    }

    assert result["current_agent_task_id"] == "T1"

    assert len(result["messages"]) >= 2
    assert result["messages"][-1].content == (
        "Final synthesized response."
    )

    event_types = [
        event.type
        for event in listener.events
    ]

    assert event_types == [
        WorkflowEventType.AGENT_TASK_CREATED,
        WorkflowEventType.AGENT_TASK_STARTED,
        WorkflowEventType.AGENT_TASK_CREATED,
        WorkflowEventType.AGENT_TASK_STARTED,
        WorkflowEventType.AGENT_MESSAGE,
        WorkflowEventType.AGENT_TASK_COMPLETED,
        WorkflowEventType.AGENT_MESSAGE,
        WorkflowEventType.AGENT_TASK_COMPLETED,
    ]

    created_root = listener.events[0]

    assert created_root.agent_task_id == "T1"
    assert created_root.agent_id == "supervisor"

    created_child = listener.events[2]

    assert created_child.agent_task_id == "T2"
    assert created_child.agent_id == "research"
    assert created_child.payload["parent_task_id"] == "T1"

    child_completed = listener.events[5]

    assert child_completed.agent_task_id == "T2"
    assert child_completed.agent_id == "research"
    assert child_completed.payload["result"] == {
        "answer": "Research complete."
    }

    root_completed = listener.events[7]

    assert root_completed.agent_task_id == "T1"
    assert root_completed.agent_id == "supervisor"


def test_compiled_graph_delegated_agent_plans_executes_and_returns_to_parent():

    listener = FakeListener()

    event_bus = EventBus()
    event_bus.subscribe(listener)

    from registry import (
        Tool,
        clear_registry as clear_tool_registry,
        register_tool,
    )

    clear_tool_registry()

    def research_tool(state):

        return {
            "messages": [],
            "output": {
                "research": "Research result."
            },
            "success": True,
            "error": None,
        }

    register_tool(
        Tool(
            name="research_test_tool",
            function=research_tool,
            description="Returns a deterministic research result.",
            outputs=["research"],
        )
    )

    decisions = [
        AgentDecision(
            action=AgentAction.DELEGATE,
            target_agent_id="research",
            request="Research the assigned subject.",
        ),
        AgentDecision(
            action=AgentAction.PLAN,
        ),
        AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Research completed from tool execution."
            },
        ),
        AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Final answer."
            },
        ),
    ]

    from models.plan import PlanStep

    planned_step = PlanStep(
        id=1,
        tool="research_test_tool",
        tool_input="Research the assigned subject.",
        depends_on=[],
    )

    class FakeAgentRuntime:

        def __init__(self):
            pass

        def decide_task(self, *args, **kwargs):
            return decisions.pop(0)

        def plan_task(self, task, existing_steps=None):
            return [
                PlanStep(
                    id=planned_step.id,
                    tool=planned_step.tool,
                    tool_input=planned_step.tool_input,
                    depends_on=planned_step.depends_on,
                    agent_task_id=task.task_id,
                )
            ]

    try:

        with patch(
            "agents.runtime.AgentRuntime",
            FakeAgentRuntime,
        ), patch(
            "langchain_core.language_models.BaseChatModel.invoke"
        ) as mock_llm:

            mock_llm.return_value.content = (
                "Final synthesized response."
            )

            state = {
                "workflow_id": "multi-agent-planning-integration-test",
                "messages": [
                    HumanMessage(
                        content="Research the assigned subject."
                    )
                ],
                "agent_tasks": {},
                "agent_messages": [],
                "current_agent_task_id": None,
                "steps": [],
                "tool_results": {},
                "execution_records": [],
                "context": {},
                "output": {},
                "runtime_config": RuntimeConfig(),
                "event_bus": event_bus,
                "error": None,
                "done": False,
            }

            result = app.invoke(state)

    finally:
        clear_tool_registry()

    assert result["error"] is None

    root = result["agent_tasks"]["T1"]
    child = result["agent_tasks"]["T2"]

    assert root.status == AgentTaskStatus.COMPLETED

    assert child.status == AgentTaskStatus.COMPLETED

    assert child.parent_task_id == "T1"
    assert child.agent_id == "research"

    assert child.result == {
        "answer": "Research completed from tool execution."
    }

    assert root.metadata["child_results"] == [
        {
            "task_id": "T2",
            "agent_id": "research",
            "request": "Research the assigned subject.",
            "result": {
                "answer": "Research completed from tool execution."
            },
        }
    ]

    assert len(result["steps"]) == 1

    step = result["steps"][0]

    assert step.tool == "research_test_tool"
    assert step.agent_task_id == "T2"

    assert 1 in result["tool_results"]

    tool_result = result["tool_results"][1]

    assert tool_result["success"] is True
    assert tool_result["output"] == {
        "research": "Research result."
    }

    assert len(result["execution_records"]) == 1

    record = result["execution_records"][0]

    assert record.step_id == 1
    assert record.agent_task_id == "T2"

    assert result["current_agent_task_id"] == "T1"

    assert result["messages"][-1].content == (
        "Final synthesized response."
    )

    event_types = [
        event.type
        for event in listener.events
    ]

    assert WorkflowEventType.AGENT_TASK_CREATED in event_types
    assert WorkflowEventType.AGENT_TASK_STARTED in event_types
    assert WorkflowEventType.AGENT_TASK_COMPLETED in event_types
    assert WorkflowEventType.AGENT_MESSAGE in event_types


def test_compiled_graph_supports_nested_delegation():

    listener = FakeListener()

    event_bus = EventBus()
    event_bus.subscribe(listener)

    register_agent(
        AgentDefinition(
            id="calculation",
            name="Calculation Agent",
            role="calculation",
            instructions="Perform calculations.",
        )
    )

    decisions = [
        # T1 Supervisor → T2 Research
        AgentDecision(
            action=AgentAction.DELEGATE,
            target_agent_id="research",
            request="Research the assigned subject.",
        ),

        # T2 Research → T3 Calculation
        AgentDecision(
            action=AgentAction.DELEGATE,
            target_agent_id="calculation",
            request="Calculate the required value.",
        ),

        # T3 Calculation → COMPLETE
        AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Calculation complete."
            },
        ),

        # T2 Research → COMPLETE
        AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Research complete."
            },
        ),

        # T1 Supervisor → COMPLETE
        AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Final answer."
            },
        ),
    ]

    with patch(
        "agents.runtime.AgentRuntime.decide_task",
        side_effect=decisions,
    ) as mock_decide, patch(
        "langchain_core.language_models.BaseChatModel.invoke"
    ) as mock_llm:

        mock_llm.return_value.content = (
            "Final synthesized response."
        )

        state = {
            "workflow_id": "nested-agent-integration-test",
            "messages": [
                HumanMessage(
                    content=(
                        "Research and calculate the assigned subject."
                    )
                )
            ],
            "agent_tasks": {},
            "agent_messages": [],
            "current_agent_task_id": None,
            "steps": [],
            "tool_results": {},
            "execution_records": [],
            "context": {},
            "output": {},
            "runtime_config": RuntimeConfig(),
            "event_bus": event_bus,
            "error": None,
            "done": False,
        }

        result = app.invoke(state)

    assert result["error"] is None

    assert mock_decide.call_count == 5

    assert set(result["agent_tasks"]) == {
        "T1",
        "T2",
        "T3",
    }

    root = result["agent_tasks"]["T1"]
    research = result["agent_tasks"]["T2"]
    calculation = result["agent_tasks"]["T3"]

    assert root.parent_task_id is None
    assert root.agent_id == "supervisor"
    assert root.status == AgentTaskStatus.COMPLETED

    assert research.parent_task_id == "T1"
    assert research.agent_id == "research"
    assert research.status == AgentTaskStatus.COMPLETED

    assert calculation.parent_task_id == "T2"
    assert calculation.agent_id == "calculation"
    assert calculation.status == AgentTaskStatus.COMPLETED

    assert calculation.result == {
        "answer": "Calculation complete."
    }

    assert research.result == {
        "answer": "Research complete."
    }

    assert root.metadata["child_results"] == [
        {
            "task_id": "T2",
            "agent_id": "research",
            "request": "Research the assigned subject.",
            "result": {
                "answer": "Research complete."
            },
        }
    ]

    assert research.metadata["child_results"] == [
        {
            "task_id": "T3",
            "agent_id": "calculation",
            "request": "Calculate the required value.",
            "result": {
                "answer": "Calculation complete."
            },
        }
    ]

    assert len(result["agent_messages"]) == 4

    assert result["agent_messages"][0].sender == "supervisor"
    assert result["agent_messages"][0].recipient == "research"
    assert result["agent_messages"][0].task_id == "T2"

    assert result["agent_messages"][1].sender == "research"
    assert result["agent_messages"][1].recipient == "calculation"
    assert result["agent_messages"][1].task_id == "T3"

    assert result["agent_messages"][2].sender == "calculation"
    assert result["agent_messages"][2].recipient == "research"
    assert result["agent_messages"][2].task_id == "T3"

    assert result["agent_messages"][3].sender == "research"
    assert result["agent_messages"][3].recipient == "supervisor"
    assert result["agent_messages"][3].task_id == "T2"

    assert result["current_agent_task_id"] == "T1"

    assert result["messages"][-1].content == (
        "Final synthesized response."
    )

    event_types = [
        event.type
        for event in listener.events
    ]

    assert event_types == [
        WorkflowEventType.AGENT_TASK_CREATED,
        WorkflowEventType.AGENT_TASK_STARTED,
        WorkflowEventType.AGENT_TASK_CREATED,
        WorkflowEventType.AGENT_TASK_STARTED,
        WorkflowEventType.AGENT_MESSAGE,
        WorkflowEventType.AGENT_TASK_CREATED,
        WorkflowEventType.AGENT_TASK_STARTED,
        WorkflowEventType.AGENT_MESSAGE,
        WorkflowEventType.AGENT_TASK_COMPLETED,
        WorkflowEventType.AGENT_MESSAGE,
        WorkflowEventType.AGENT_TASK_COMPLETED,
        WorkflowEventType.AGENT_MESSAGE,
        WorkflowEventType.AGENT_TASK_COMPLETED,
    ]

def test_compiled_graph_executes_weather_tool_end_to_end():

    listener = FakeListener()

    event_bus = EventBus()
    event_bus.subscribe(listener)

    from registry import clear_registry as clear_tool_registry
    import tools

    clear_tool_registry()
    import importlib
    importlib.reload(tools)

    decisions = [
        AgentDecision(
            action=AgentAction.PLAN,
        ),
        AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "The weather indicates that you should carry a raincoat."
            },
        ),
    ]

    geocoding_response = {
        "results": [
            {
                "name": "Mumbai",
                "country": "India",
                "latitude": 19.07283,
                "longitude": 72.88261,
            }
        ]
    }

    forecast_response = {
        "timezone": "Asia/Kolkata",
        "current": {
            "temperature_2m": 33.2,
            "weather_code": 0,
            "precipitation": 0,
            "rain": 0,
        },
        "hourly": {
            "time": [
                "2026-10-06T12:00",
                "2026-10-06T13:00",
            ],
            "precipitation_probability": [10, 56],
        },
    }

    class FakeResponse:

        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    responses = [
        FakeResponse(geocoding_response),
        FakeResponse(forecast_response),
    ]

    from models.plan import PlanStep

    planned_step = PlanStep(
        id=1,
        tool="weather",
        tool_input="Mumbai, India",
        depends_on=[],
        agent_task_id="T1",
    )

    try:
        with (
            patch(
                "agents.runtime.AgentRuntime.decide_task",
                side_effect=decisions,
            ),
            patch(
                "agents.runtime.AgentRuntime.plan_task",
                return_value=[planned_step],
            ),
            patch(
                "tools.weather.httpx.Client",
            ) as mock_client,
            patch(
                "langchain_core.language_models.BaseChatModel.invoke",
            ) as mock_llm,
        ):
            client = mock_client.return_value.__enter__.return_value
            client.get.side_effect = responses

            mock_llm.return_value.content = (
                "The weather indicates that you should carry a raincoat."
            )

            state = {
                "workflow_id": "weather-integration-test",
                "messages": [
                    HumanMessage(
                        content="Should I carry a raincoat in Mumbai today?"
                    )
                ],
                "agent_tasks": {},
                "agent_messages": [],
                "current_agent_task_id": None,
                "steps": [],
                "tool_results": {},
                "execution_records": [],
                "context": {},
                "output": {},
                "runtime_config": RuntimeConfig(),
                "event_bus": event_bus,
                "error": None,
                "done": False,
            }

            result = app.invoke(state)

    finally:
        clear_tool_registry()

    assert result["error"] is None

    assert len(result["steps"]) == 1

    step = result["steps"][0]
    assert step.tool == "weather"

    assert 1 in result["tool_results"]

    weather_result = result["tool_results"][1]

    assert weather_result["success"] is True
    assert weather_result["output"]["location"] == "Mumbai"
    assert weather_result["output"]["country"] == "India"
    assert (
        weather_result["output"]["today"]["max_precipitation_probability"]
        == 56
    )

    assert result["execution_records"][0].tool == "weather"
    assert result["execution_records"][0].success is True

    assert result["messages"][-1].content == (
        "The weather indicates that you should carry a raincoat."
    )