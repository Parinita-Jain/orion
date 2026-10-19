
from uuid import uuid4

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from runtime.llm_usage import LLMUsageTracker


def test_tracker_records_success_and_token_usage():
    tracker = LLMUsageTracker()
    run_id = uuid4()

    tracker.on_chat_model_start(
        {"name": "gemini-2.5-flash"},
        [[]],
        run_id=run_id,
        metadata={"model_name": "gemini-2.5-flash"},
    )

    response = LLMResult(
        generations=[
            [
                ChatGeneration(
                    message=AIMessage(
                        content="Hello",
                        usage_metadata={
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "total_tokens": 15,
                        },
                    )
                )
            ]
        ]
    )

    tracker.on_llm_end(response, run_id=run_id)

    result = tracker.snapshot()

    assert result["totals"]["attempts"] == 1
    assert result["totals"]["successes"] == 1
    assert result["totals"].get("failures", 0) == 0
    assert result["models"]["gemini-2.5-flash"]["input_tokens"] == 10
    assert result["models"]["gemini-2.5-flash"]["output_tokens"] == 5
    assert result["models"]["gemini-2.5-flash"]["total_tokens"] == 15
    assert result["in_flight"] == 0


def test_tracker_records_failed_invocation():
    tracker = LLMUsageTracker()
    run_id = uuid4()

    tracker.on_chat_model_start(
        {"name": "gemini-2.5-flash"},
        [[]],
        run_id=run_id,
        metadata={"model_name": "gemini-2.5-flash"},
    )

    tracker.on_llm_error(
        RuntimeError("Simulated quota error"),
        run_id=run_id,
    )

    result = tracker.snapshot()

    assert result["totals"]["attempts"] == 1
    assert result["totals"]["failures"] == 1
    assert result["totals"].get("successes", 0) == 0
    assert result["in_flight"] == 0
