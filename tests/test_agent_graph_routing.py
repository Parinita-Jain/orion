from shared_types.completion_status import CompletionStatus

from workflow.graph import (
    route_after_agent,
    route_after_completion,
    route_after_replanner,
)


def test_agent_routes_to_planner():

    assert (
        route_after_agent(
            {
                "agent_next_node": "planner",
                "error": None,
            }
        )
        == "planner"
    )


def test_agent_routes_back_to_agent():

    assert (
        route_after_agent(
            {
                "agent_next_node": "agent",
                "error": None,
            }
        )
        == "agent"
    )


def test_agent_routes_root_completion_to_synthesizer():

    assert (
        route_after_agent(
            {
                "agent_next_node": "synthesizer",
                "error": None,
            }
        )
        == "synthesizer"
    )


def test_completion_routes_to_agent():

    assert (
        route_after_completion(
            {
                "completion_status":
                    CompletionStatus.COMPLETE,
            }
        )
        == "agent"
    )


def test_replanner_done_routes_to_agent():

    assert (
        route_after_replanner(
            {
                "done": True,
                "error": None,
            }
        )
        == "agent"
    )