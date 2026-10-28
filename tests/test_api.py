from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("api.main.workflow_app.invoke")
def test_execute_workflow_success(mock_invoke):
    from langchain_core.messages import AIMessage

    mock_invoke.return_value = {
        "messages": [AIMessage(content="Hello! How can I help you?")]
    }

    response = client.post(
        "/workflow",
        json={"question": "Hello"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["answer"] == "Hello! How can I help you?"
    assert data["workflow_id"]

    mock_invoke.assert_called_once()


def test_execute_workflow_rejects_empty_question():
    response = client.post(
        "/workflow",
        json={"question": ""},
    )

    assert response.status_code == 422


@patch("api.main.workflow_app.invoke")
def test_execute_workflow_failure(mock_invoke):
    mock_invoke.side_effect = RuntimeError("Simulated workflow failure")

    response = client.post(
        "/workflow",
        json={"question": "Hello"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Workflow execution failed."

@patch("api.main.workflow_app.invoke")
def test_execute_workflow_uses_independent_state_for_each_request(mock_invoke):
    from langchain_core.messages import AIMessage

    captured_states = []

    def fake_invoke(state):
        captured_states.append(state)
        return {"messages": [AIMessage(content="Test response")]}

    mock_invoke.side_effect = fake_invoke

    response1 = client.post(
        "/workflow",
        json={"question": "First question"},
    )
    response2 = client.post(
        "/workflow",
        json={"question": "Second question"},
    )

    assert response1.status_code == 200
    assert response2.status_code == 200

    assert response1.json()["workflow_id"] != response2.json()["workflow_id"]

    assert len(captured_states) == 2
    state1, state2 = captured_states

    assert state1 is not state2
    assert state1["messages"] is not state2["messages"]
    assert state1["event_bus"] is not state2["event_bus"]
    assert state1["tool_results"] is not state2["tool_results"]
    assert state1["workflow_id"] != state2["workflow_id"]

    assert state1["messages"][0].content == "First question"
    assert state2["messages"][0].content == "Second question"


@patch("runtime.stream.app.invoke")
def test_workflow_stream_emits_sse_events(mock_invoke):
    from runtime.event import WorkflowEvent
    from shared_types.workflow_event_type import WorkflowEventType

    def fake_invoke(state):
        state["event_bus"].emit(
            WorkflowEvent(
                type=WorkflowEventType.WORKFLOW_STARTED,
                payload={"workflow_id": state["workflow_id"]},
            )
        )
        state["event_bus"].emit(
            WorkflowEvent(
                type=WorkflowEventType.WORKFLOW_COMPLETED,
            )
        )
        return state

    mock_invoke.side_effect = fake_invoke

    response = client.post(
        "/workflow/stream",
        json={"question": "Hello"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: workflow_started" in response.text
    assert "event: workflow_completed" in response.text
    assert '"type": "workflow_started"' in response.text
    assert '"payload":' in response.text
    mock_invoke.assert_called_once()


@patch("api.main.workflow_app.invoke")
def test_execute_workflow_returns_error_when_workflow_handles_failure(mock_invoke):
    from errors import OrionError, ErrorType
    from langchain_core.messages import AIMessage

    mock_invoke.return_value = {
        "messages": [
            AIMessage(
                content="The AI service is temporarily unavailable. "
                        "Please try again in a few minutes."
            )
        ],
        "error": OrionError(
            source="planner",
            error_type=ErrorType.INFRASTRUCTURE,
            message="Gemini quota exceeded",
            recoverable=True,
        ),
        "done": True,
    }

    response = client.post(
        "/workflow",
        json={"question": "Explain RAG"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Workflow execution failed."


@patch("runtime.stream.app.invoke")
def test_workflow_stream_reports_generic_error(mock_invoke):
    mock_invoke.side_effect = RuntimeError(
        "Internal provider details must not be exposed"
    )

    response = client.post(
        "/workflow/stream",
        json={"question": "Test streaming failure"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: error" in response.text
    assert '"detail":"Workflow execution failed."' in response.text
    assert "Internal provider details must not be exposed" not in response.text
    mock_invoke.assert_called_once()


@patch("api.main.stream_workflow")
def test_workflow_stream_closes_stream_when_generator_closes(
    mock_stream_workflow,
):
    import asyncio

    from runtime.event import WorkflowEvent
    from shared_types.workflow_event_type import WorkflowEventType
    from api.main import stream_workflow_endpoint, WorkflowRequest

    class FakeStream:
        error = None

        def __init__(self):
            self.closed = False

        def __iter__(self):
            yield WorkflowEvent(
                type=WorkflowEventType.WORKFLOW_STARTED,
            )

        def close(self):
            self.closed = True

    fake_stream = FakeStream()
    mock_stream_workflow.return_value = fake_stream

    response = stream_workflow_endpoint(
        WorkflowRequest(question="Test cleanup")
    )

    async def consume_and_close():
        generator = response.body_iterator
        await generator.__anext__()
        await generator.aclose()

    asyncio.run(consume_and_close())

    assert fake_stream.closed is True
