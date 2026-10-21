from unittest.mock import Mock

import pytest
from google.genai.errors import APIError

from runtime.llm_fallback import QuotaAwareLLM


def test_falls_back_when_primary_hits_quota():
    primary = Mock()
    fallback = Mock()
    primary.invoke.side_effect = APIError(
        429, {"message": "Resource exhausted"}
    )
    fallback.invoke.return_value = "fallback response"

    llm = QuotaAwareLLM(primary, fallback)

    result = llm.invoke("test prompt")

    assert result == "fallback response"
    primary.invoke.assert_called_once_with("test prompt")
    fallback.invoke.assert_called_once_with("test prompt")


def test_does_not_fall_back_for_other_errors():
    primary = Mock()
    fallback = Mock()
    primary.invoke.side_effect = ValueError("Invalid input")

    llm = QuotaAwareLLM(primary, fallback)

    with pytest.raises(ValueError, match="Invalid input"):
        llm.invoke("test prompt")

    fallback.invoke.assert_not_called()


def test_propagates_quota_error_when_fallback_is_not_configured():
    primary = Mock()
    primary.invoke.side_effect = APIError(
        429, {"message": "Resource exhausted"}
    )

    llm = QuotaAwareLLM(primary)

    with pytest.raises(APIError):
        llm.invoke("test prompt")


def test_structured_output_wraps_both_models():
    primary = Mock()
    fallback = Mock()
    primary_structured = Mock()
    fallback_structured = Mock()
    primary.with_structured_output.return_value = primary_structured
    fallback.with_structured_output.return_value = fallback_structured

    llm = QuotaAwareLLM(primary, fallback)
    structured_llm = llm.with_structured_output(dict)

    assert structured_llm._primary is primary_structured
    assert structured_llm._fallback is fallback_structured
