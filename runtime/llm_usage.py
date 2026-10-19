
from collections import Counter
from threading import Lock
from time import perf_counter
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler


class LLMUsageTracker(BaseCallbackHandler):
    """Track LLM invocation attempts, outcomes, duration, and token usage."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._starts: dict[UUID, tuple[str, float]] = {}
        self._totals: Counter[str] = Counter()
        self._models: dict[str, Counter[str]] = {}

    @staticmethod
    def _model_name(
        serialized: dict[str, Any] | None,
        kwargs: dict[str, Any] | None = None,
    ) -> str:
        """Extract a model name from callback metadata when available."""
        kwargs = kwargs or {}
        serialized = serialized or {}

        metadata = kwargs.get("metadata") or {}
        invocation_params = kwargs.get("invocation_params") or {}

        model = (
            metadata.get("ls_model_name")
            or metadata.get("model_name")
            or invocation_params.get("model")
            or invocation_params.get("model_name")
            or serialized.get("name")
        )

        if not model:
            model = "unknown"

        return str(model)

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        model = self._model_name(
            serialized,
            {"metadata": metadata, **kwargs},
        )

        with self._lock:
            self._starts[run_id] = (model, perf_counter())
            self._totals["attempts"] += 1
            self._models.setdefault(model, Counter())["attempts"] += 1

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # Handles traditional LLMs. Chat models use on_chat_model_start.
        model = self._model_name(
            serialized,
            {"metadata": metadata, **kwargs},
        )

        with self._lock:
            self._starts[run_id] = (model, perf_counter())
            self._totals["attempts"] += 1
            self._models.setdefault(model, Counter())["attempts"] += 1

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self._finish(run_id, success=True, response=response)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self._finish(run_id, success=False)

    def _finish(
        self,
        run_id: UUID,
        *,
        success: bool,
        response: Any = None,
    ) -> None:
        with self._lock:
            started = self._starts.pop(run_id, None)

            # Ignore completion events without a matching start.
            if started is None:
                return

            model, start_time = started
            model_stats = self._models.setdefault(model, Counter())
            duration = perf_counter() - start_time

            outcome = "successes" if success else "failures"
            self._totals[outcome] += 1
            model_stats[outcome] += 1

            self._totals["duration_seconds_millis"] += round(duration * 1000)
            model_stats["duration_seconds_millis"] += round(duration * 1000)

            if success and response is not None:
                self._record_tokens(model_stats, response)

    @staticmethod
    def _record_tokens(stats: Counter[str], response: Any) -> None:
        """Record token counts when supplied by the model response."""
        for generation_group in getattr(response, "generations", []):
            for generation in generation_group:
                message = getattr(generation, "message", None)
                usage = getattr(message, "usage_metadata", None) or {}

                if not isinstance(usage, dict):
                    continue

                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                total_tokens = usage.get(
                    "total_tokens",
                    input_tokens + output_tokens,
                )

                stats["input_tokens"] += input_tokens
                stats["output_tokens"] += output_tokens
                stats["total_tokens"] += total_tokens

    def snapshot(self) -> dict[str, Any]:
        """Return a thread-safe snapshot of all counters."""
        with self._lock:
            return {
                "totals": dict(self._totals),
                "models": {
                    model: dict(stats)
                    for model, stats in self._models.items()
                },
                "in_flight": len(self._starts),
            }
