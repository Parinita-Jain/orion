from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from state import AgentState

from workflow.nodes import (
    agent_node,
    planner_node,
    executor_node,
)

from .completion import completion_node

from replanner import replanner_node

from synthesizer import synthesizer_node

from error_handler import error_handler_node

from shared_types.completion_status import CompletionStatus


workflow = StateGraph(
    AgentState
)


workflow.add_node(
    "agent",
    agent_node,
)

workflow.add_node(
    "planner",
    planner_node,
)

workflow.add_node(
    "executor",
    executor_node,
)

workflow.add_node(
    "completion",
    completion_node,
)

workflow.add_node(
    "replanner",
    replanner_node,
)

workflow.add_node(
    "synthesizer",
    synthesizer_node,
)

workflow.add_node(
    "error_handler",
    error_handler_node,
)


def route_after_agent(state):

    if state.get("error"):
        return "error"

    return state.get(
        "agent_next_node",
        "error",
    )

def _is_legacy_workflow(state):
    return (
        not state.get("agent_tasks")
        and state.get("current_agent_task_id") is None
        and bool(state.get("steps"))
    )

def route_after_completion(state):

    status = state["completion_status"]

    if status == CompletionStatus.COMPLETE:
        if _is_legacy_workflow(state):
            return "synthesizer"
        return "agent"

    if status == CompletionStatus.CONTINUE:
        return "executor"

    if status == CompletionStatus.REPLAN:
        return "replanner"

    return "error_handler"


def route_after_planner(state):

    if state.get("error"):
        return "error"

    return "executor"

def route_after_replanner(state):

    if state.get("error"):
        return "error"

    if state.get("done"):
        if _is_legacy_workflow(state):
            return "synthesizer"

        return "agent"

    return "executor"


def route_after_synthesizer(state):

    if state.get("error"):
        return "error"

    return "done"


def route_after_start(state):

    if state.get("resume"):

        if (
            state.get(
                "completion_status"
            )
            == CompletionStatus.REPLAN
        ):
            return "replanner"

        return "executor"

    return "agent"


workflow.add_conditional_edges(
    START,
    route_after_start,
    {
        "agent": "agent",
        "executor": "executor",
        "replanner": "replanner",
    },
)


workflow.add_conditional_edges(
    "agent",
    route_after_agent,
    {
        "planner": "planner",
        "agent": "agent",
        "synthesizer": "synthesizer",
        "error": "error_handler",
    },
)


workflow.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "executor": "executor",
        "error": "error_handler",
    },
)


workflow.add_edge(
    "executor",
    "completion",
)


workflow.add_conditional_edges(
    "completion",
    route_after_completion,
    {
        "agent": "agent",
        "executor": "executor",
        "replanner": "replanner",
        "error_handler": "error_handler",
        "synthesizer": "synthesizer",
    },
)


workflow.add_conditional_edges(
    "replanner",
    route_after_replanner,
    {
        "agent": "agent",
        "executor": "executor",
        "error": "error_handler",
    },
)


workflow.add_conditional_edges(
    "synthesizer",
    route_after_synthesizer,
    {
        "done": END,
        "error": "error_handler",
    },
)


workflow.add_edge(
    "error_handler",
    END,
)


app = workflow.compile()