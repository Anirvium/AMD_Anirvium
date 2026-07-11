from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import time
from typing import Dict, List, Protocol

import httpx

from app.config import Settings, get_settings


logger = logging.getLogger("uvicorn.error")


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
            "max_tokens": self.settings.llm_max_tokens,
        }
        if self.settings.llm_disable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        started_at = time.perf_counter()
        logger.info("llm_call_started model=%s messages=%s", self.settings.llm_model, len(messages))
        try:
            with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
                response = client.post(
                    f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                # Older OpenAI-compatible servers may not implement vLLM's
                # Qwen chat-template switch. Retry once without that extension
                # while retaining the output-token bound.
                if response.status_code == 400 and "chat_template_kwargs" in payload:
                    logger.warning(
                        "llm_thinking_control_unsupported model=%s retrying_without_extension=true",
                        self.settings.llm_model,
                    )
                    payload.pop("chat_template_kwargs", None)
                    response = client.post(
                        f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                response.raise_for_status()
                data = response.json()
        except Exception:
            logger.exception(
                "llm_call_failed model=%s duration_ms=%s",
                self.settings.llm_model,
                int((time.perf_counter() - started_at) * 1000),
            )
            raise
        content = data["choices"][0]["message"]["content"]
        cleaned_content = strip_private_reasoning(content)
        usage = data.get("usage", {})
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "llm_call_completed model=%s duration_ms=%s prompt_tokens=%s completion_tokens=%s raw_chars=%s public_chars=%s",
            self.settings.llm_model,
            elapsed_ms,
            usage.get("prompt_tokens", estimate_tokens(messages)),
            usage.get("completion_tokens", estimate_tokens(content)),
            len(content),
            len(cleaned_content),
        )
        return LLMResponse(
            text=cleaned_content,
            model_name=self.settings.llm_model,
            tokens_in=usage.get("prompt_tokens", estimate_tokens(messages)),
            tokens_out=usage.get("completion_tokens", estimate_tokens(content)),
            latency_ms=elapsed_ms,
        )


def build_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider.lower() in {"openai", "openai_compatible", "llm"}:
        return OpenAICompatibleLLMClient(settings)
    return MockLLMClient()
