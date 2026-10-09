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
