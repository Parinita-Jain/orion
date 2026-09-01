from langgraph.graph import StateGraph, START, END

from state import AgentState

from workflow.nodes import (
    agent_node,
    planner_node,
    executor_node
)
from .completion import completion_node
from replanner import replanner_node
from synthesizer import synthesizer_node
from error_handler import error_handler_node

from shared_types.completion_status import CompletionStatus

# Create Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("agent", agent_node)
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)
workflow.add_node("completion",completion_node)
workflow.add_node("replanner",replanner_node)
workflow.add_node("synthesizer", synthesizer_node)
workflow.add_node("error_handler",error_handler_node)

def route_after_completion(state):

    status = state["completion_status"]

    if status == CompletionStatus.COMPLETE:
        return "synthesizer"

    if status == CompletionStatus.CONTINUE:
        return "executor"

    if status == CompletionStatus.REPLAN:
        return "replanner"

    return "error_handler"

def route_after_planner(state):

    print(state)

    if state.get("error"):
        return "error"

    return "executor"


def route_after_replanner(state):

    if state.get("error"):
        return "error"

    if state.get("done"):
        return "synthesizer"

    return "executor"

def route_after_synthesizer(state):

    if state.get("error"):
        return "error"

    return "done"

# Start Flow
def route_after_start(state):
    if state.get("resume"):
        return "executor"

    return "agent"

workflow.add_conditional_edges(
    START,
    route_after_start,
    {
        "agent": "agent",
        "executor": "executor",
    },
)

# Agent → Planner
workflow.add_edge("agent", "planner")
# Routing
workflow.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "executor": "executor",
        "error": "error_handler"
    }
)
# RAG Path
workflow.add_edge(
    "executor",
    "completion"
)
workflow.add_conditional_edges(
    "completion",
    route_after_completion,
    {
        "synthesizer": "synthesizer",
        "executor": "executor",
        "replanner": "replanner",
        "error": "error_handler",
    },
)
workflow.add_conditional_edges(
    "replanner",
     route_after_replanner,
    {
        "executor": "executor",
        "synthesizer": "synthesizer",
        "error": "error_handler"
    }
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
    END
)

# Compile Graph
app = workflow.compile()