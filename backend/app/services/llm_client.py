from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, List, Protocol

import httpx

from app.config import Settings, get_settings


@dataclass
class LLMResponse:
    text: str
    model_name: str
    tokens_in: int
    tokens_out: int
    latency_ms: int = 0


class LLMClient(Protocol):
    model_name: str

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> LLMResponse:
        ...


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", flags=re.IGNORECASE | re.DOTALL)
_INCOMPLETE_THINK_RE = re.compile(r"<think>.*$", flags=re.IGNORECASE | re.DOTALL)


def strip_private_reasoning(text: str) -> str:
    without_closed_blocks = _THINK_BLOCK_RE.sub("", text)
    without_incomplete_block = _INCOMPLETE_THINK_RE.sub("", without_closed_blocks)
    cleaned = without_incomplete_block.replace("</think>", "")
    return " ".join(cleaned.split())


def estimate_tokens(value: object) -> int:
    text = str(value)
    # This is intentionally conservative for demo telemetry, not billing.
    return max(1, len(text.split()) + len(text) // 16)


class MockLLMClient:
    model_name = "mock-trajectory-model"

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> LLMResponse:
        prompt = "\n".join(message.get("content", "") for message in messages)
        text = "Deterministic mock response generated from local trajectory rules."
        return LLMResponse(
            text=text,
            model_name=self.model_name,
            tokens_in=estimate_tokens(prompt),
            tokens_out=estimate_tokens(text),
        )


class OpenAICompatibleLLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model_name = settings.llm_model

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> LLMResponse:
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key or 'dummy'}"}
        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            response = client.post(
                f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        cleaned_content = strip_private_reasoning(content)
        usage = data.get("usage", {})
        return LLMResponse(
            text=cleaned_content,
            model_name=self.settings.llm_model,
            tokens_in=usage.get("prompt_tokens", estimate_tokens(messages)),
            tokens_out=usage.get("completion_tokens", estimate_tokens(content)),
        )


def build_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider.lower() in {"openai", "openai_compatible", "llm"}:
        return OpenAICompatibleLLMClient(settings)
    return MockLLMClient()
