from agents import AgentMessage


def test_agent_message():
    message = AgentMessage(
        message_id="M1",
        sender="supervisor",
        recipient="research",
        content="Research this subject.",
        task_id="T2",
        correlation_id="C1",
    )

    assert message.message_id == "M1"
    assert message.sender == "supervisor"
    assert message.recipient == "research"
    assert message.content == "Research this subject."
    assert message.task_id == "T2"
    assert message.correlation_id == "C1"