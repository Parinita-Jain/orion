from agents import AgentTask, AgentTaskStatus


def test_agent_task_defaults():
    task = AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="supervisor",
        request="Handle the user request.",
    )

    assert task.status == AgentTaskStatus.CREATED
    assert task.result is None
    assert task.metadata == {}


def test_agent_task_parent_relationship():
    task = AgentTask(
        task_id="T2",
        parent_task_id="T1",
        agent_id="research",
        request="Research the subject.",
    )

    assert task.parent_task_id == "T1"
    assert task.agent_id == "research"