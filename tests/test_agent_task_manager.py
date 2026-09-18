import pytest

from agents.models import AgentDefinition
from agents.registry import (
    clear_registry,
    register_agent,
)

from agents.task import AgentTaskStatus

from agents.task_manager import (
    cancel_task,
    complete_task,
    create_child_task,
    fail_task,
    get_parent_task,
    get_task,
    next_task_id,
    start_task,
)


@pytest.fixture(autouse=True)
def clean_registry():
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

    yield

    clear_registry()


def make_root():
    from agents.task import AgentTask

    return AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="supervisor",
        request="Complete the user request.",
        status=AgentTaskStatus.RUNNING,
    )


def test_next_task_id():
    agent_tasks = {
        "T1": make_root(),
        "T2": make_root(),
    }

    assert next_task_id(agent_tasks) == "T3"


def test_create_child_task():
    agent_tasks = {
        "T1": make_root(),
    }

    child = create_child_task(
        agent_tasks,
        parent_task_id="T1",
        agent_id="research",
        request="Research the assigned subject.",
    )

    assert child.task_id == "T2"
    assert child.parent_task_id == "T1"
    assert child.agent_id == "research"
    assert child.request == (
        "Research the assigned subject."
    )
    assert child.status == AgentTaskStatus.ASSIGNED
    assert child.metadata["delegated_by"] == "T1"
    assert agent_tasks["T2"] is child


def test_create_child_requires_registered_agent():
    agent_tasks = {
        "T1": make_root(),
    }

    with pytest.raises(
        ValueError,
        match="is not registered",
    ):
        create_child_task(
            agent_tasks,
            parent_task_id="T1",
            agent_id="unknown",
            request="Do some work.",
        )


def test_child_lifecycle_and_result_return():
    agent_tasks = {
        "T1": make_root(),
    }

    child = create_child_task(
        agent_tasks,
        parent_task_id="T1",
        agent_id="research",
        request="Research the assigned subject.",
    )

    start_task(
        agent_tasks,
        child.task_id,
    )

    result = {
        "answer": "Research completed."
    }

    complete_task(
        agent_tasks,
        child.task_id,
        result=result,
    )

    assert (
        agent_tasks["T2"].status
        == AgentTaskStatus.COMPLETED
    )

    assert (
        agent_tasks["T2"].result
        == result
    )

    assert (
        agent_tasks["T1"].metadata[
            "child_results"
        ][0]["task_id"]
        == "T2"
    )

    assert (
        agent_tasks["T1"].metadata[
            "child_results"
        ][0]["result"]
        == result
    )


def test_get_parent_task():
    agent_tasks = {
        "T1": make_root(),
    }

    child = create_child_task(
        agent_tasks,
        parent_task_id="T1",
        agent_id="research",
        request="Research the subject.",
    )

    assert (
        get_parent_task(
            agent_tasks,
            child.task_id,
        )
        is agent_tasks["T1"]
    )

    assert (
        get_parent_task(
            agent_tasks,
            "T1",
        )
        is None
    )


def test_fail_task_returns_failure_to_parent():
    agent_tasks = {
        "T1": make_root(),
    }

    child = create_child_task(
        agent_tasks,
        parent_task_id="T1",
        agent_id="research",
        request="Research the subject.",
    )

    start_task(
        agent_tasks,
        child.task_id,
    )

    failure = {
        "error": "Research failed."
    }

    fail_task(
        agent_tasks,
        child.task_id,
        result=failure,
    )

    assert (
        agent_tasks["T2"].status
        == AgentTaskStatus.FAILED
    )

    assert (
        agent_tasks["T1"].metadata[
            "child_results"
        ][0]["status"]
        == "failed"
    )


def test_cancel_task():
    agent_tasks = {
        "T1": make_root(),
    }

    child = create_child_task(
        agent_tasks,
        parent_task_id="T1",
        agent_id="research",
        request="Research the subject.",
    )

    cancel_task(
        agent_tasks,
        child.task_id,
    )

    assert (
        agent_tasks["T2"].status
        == AgentTaskStatus.CANCELLED
    )


def test_missing_task_is_rejected():
    with pytest.raises(
        ValueError,
        match="does not exist",
    ):
        get_task(
            {},
            "T99",
        )