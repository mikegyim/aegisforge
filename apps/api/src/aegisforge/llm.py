"""LLM provider abstraction.

Real providers (Anthropic, OpenAI, Bedrock) are loaded lazily so the package
remains importable in environments without those SDKs (and without API keys).
The deterministic ``MockProvider`` is the default, which makes tests reproducible
and lets the project run offline.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from .config import Settings, get_settings

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when an LLM provider call fails."""


class LLMProvider(ABC):
    name: str = "base"
    model: str = "unknown"

    @abstractmethod
    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        """Return a JSON object produced by the model."""


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from a model response."""

    text = text.strip()
    if text.startswith("```"):
        # strip code fences
        lines = [ln for ln in text.splitlines() if not ln.startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # find first { ... last }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


class MockProvider(LLMProvider):
    """Deterministic provider used in tests and offline runs.

    Produces a believable, schema-shaped response derived from the user prompt
    so that downstream code paths get exercised without network access.
    """

    name = "mock"
    model = "mock-reasoner-v1"

    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        # Heuristics keep responses varied but reproducible.
        lower = user.lower()
        is_security = "security" in lower or "falco" in lower or "shell" in lower
        is_memory = "memory" in lower or "oom" in lower
        if is_security:
            cause = "Likely unauthorized in-pod command execution (possible compromise)."
            recommendation = "Isolate workload via NetworkPolicy and trigger forensic capture."
        elif is_memory:
            cause = "Memory pressure due to workload exceeding requested limits."
            recommendation = "Raise memory requests/limits and restart the deployment."
        else:
            cause = "Anomalous infrastructure signal pending deeper inspection."
            recommendation = "Open investigation; collect logs and metrics."

        return {
            "root_cause_hypothesis": cause,
            "executive_summary": (
                "AegisForge analyzed the incoming infrastructure event, correlated "
                "findings from the observability, security, and governance agents, "
                "and produced the following recommendation: " + recommendation
            ),
            "recommended_actions": [recommendation],
            "confidence": 0.8,
        }


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str, max_tokens: int, timeout: int) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise LLMError("anthropic SDK not installed. Install aegisforge[llm].") from exc
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)
        self.model = model
        self._max_tokens = max_tokens

    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        try:
            msg = await self._client.messages.create(
                model=self.model,
                max_tokens=self._max_tokens,
                system=system + "\nRespond ONLY with valid JSON matching: " + schema_hint,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:  # pragma: no cover - network
            raise LLMError(f"anthropic call failed: {exc}") from exc
        text = "".join(getattr(block, "text", "") for block in msg.content)
        return _extract_json(text)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, max_tokens: int, timeout: int) -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise LLMError("openai SDK not installed. Install aegisforge[llm].") from exc
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self._max_tokens = max_tokens

    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                max_tokens=self._max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system + "\nSchema: " + schema_hint},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:  # pragma: no cover - network
            raise LLMError(f"openai call failed: {exc}") from exc
        text = resp.choices[0].message.content or "{}"
        return _extract_json(text)


def build_provider(settings: Settings | None = None) -> LLMProvider:
    """Factory that returns the configured provider.

    Falls back to :class:`MockProvider` when the chosen provider cannot be
    instantiated (missing key, missing SDK). This keeps the API resilient and
    makes local development friction-free.
    """

    settings = settings or get_settings()
    choice = settings.llm_provider
    try:
        if choice == "anthropic" and settings.anthropic_api_key:
            return AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                timeout=settings.llm_timeout_seconds,
            )
        if choice == "openai" and settings.openai_api_key:
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                timeout=settings.llm_timeout_seconds,
            )
    except LLMError as exc:
        log.warning("falling back to mock provider: %s", exc)
    return MockProvider()
