from typing import Any

from langchain_core.runnables import Runnable

from runtime.llm_errors import is_quota_or_rate_limit_error


class QuotaAwareLLM(Runnable):
    """Use a fallback model only when the primary model hits HTTP 429."""

    def __init__(self, primary: Any, fallback: Any | None = None) -> None:
        self._primary = primary
        self._fallback = fallback

    def invoke(
        self,
        input: Any,
        config: Any = None,
        **kwargs: Any,
    ) -> Any:
        invoke_kwargs = dict(kwargs)
        if config is not None:
            invoke_kwargs["config"] = config

        try:
            return self._primary.invoke(input, **invoke_kwargs)
        except Exception as error:
            if (
                self._fallback is None
                or not is_quota_or_rate_limit_error(error)
            ):
                raise

            return self._fallback.invoke(input, **invoke_kwargs)

    def with_structured_output(
        self,
        schema: Any,
        **kwargs: Any,
    ) -> "QuotaAwareLLM":
        primary_structured = self._primary.with_structured_output(
            schema,
            **kwargs,
        )
        fallback_structured = (
            self._fallback.with_structured_output(schema, **kwargs)
            if self._fallback is not None
            else None
        )

        return QuotaAwareLLM(
            primary=primary_structured,
            fallback=fallback_structured,
        )

    def __getattr__(self, name: str) -> Any:
        """Delegate other model attributes to the primary model."""
        return getattr(self._primary, name)
