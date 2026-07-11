from __future__ import annotations

from app.agents.response_agent import ResponseDraftingAgent
from app.config import Settings
from app.services import llm_client as llm_client_module
from app.services.llm_client import LLMResponse, OpenAICompatibleLLMClient, strip_private_reasoning


class FakeLLM:
    model_name = "fake-vllm-model"

    def generate(self, messages, temperature=0.1):  # type: ignore[no-untyped-def]
        return LLMResponse(
            text="Hi Customer, we are reviewing this with the responsible team and will not confirm any restricted action until evidence and approval are complete.",
            model_name=self.model_name,
            tokens_in=10,
            tokens_out=20,
        )


def test_response_agent_llm_path_accepts_safe_response() -> None:
    agent = ResponseDraftingAgent()
    result = agent._draft_with_llm(
        llm_client=FakeLLM(),
        ticket=type("Ticket", (), {"message": "Unblock me now", "customer_name": "Customer"})(),
        escalation={"owner": "Verification queue"},
        policy={"approval_state": "APPROVAL_REQUIRED", "constraints": ["Do not promise unblocking."]},
        fallback="Fallback safe response.",
    )

    assert result.startswith("Hi Customer")
    assert result != "Fallback safe response."


def test_private_reasoning_is_stripped_from_llm_text() -> None:
    assert strip_private_reasoning("<think>private planning</think>Final answer") == "Final answer"
    assert strip_private_reasoning("<think>unfinished private planning") == ""


def test_response_prompt_contains_generation_safe_evidence() -> None:
    captured: dict[str, object] = {}

    class CapturingLLM(FakeLLM):
        def generate(self, messages, temperature=0.1):  # type: ignore[no-untyped-def]
            captured["messages"] = messages
            return super().generate(messages, temperature)

    ResponseDraftingAgent()._draft_with_llm(
        llm_client=CapturingLLM(),
        ticket=type("Ticket", (), {"message": "Missing withdrawal", "customer_name": "Customer"})(),
        escalation={"owner": "Withdrawal review queue"},
        policy={"approval_state": "APPROVAL_REQUIRED", "constraints": []},
        retrieved_evidence=[
            {"id": "POL-CS-PAY-002", "title": "Proof gate", "summary": "Request bank evidence.", "category": "kb_policies"},
            {"id": "EVAL-CS-WDR-001", "title": "Eval only", "summary": "Never use this.", "category": "kb_eval_cases"},
        ],
        fallback="Fallback safe response.",
    )

    prompt = str(captured["messages"])
    assert "POL-CS-PAY-002" in prompt
    assert "Request bank evidence" in prompt
    assert "EVAL-CS-WDR-001" not in prompt


def test_openai_compatible_payload_bounds_qwen_generation(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "Safe final response"}}], "usage": {"prompt_tokens": 4, "completion_tokens": 4}}

    class FakeHttpClient:
        def __init__(self, timeout: int) -> None:
            captured["timeout"] = timeout

        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, *_args):  # type: ignore[no-untyped-def]
            return None

        def post(self, _url: str, *, headers: dict, json: dict):  # type: ignore[no-untyped-def]
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(llm_client_module.httpx, "Client", FakeHttpClient)
    settings = Settings(
        llm_provider="openai_compatible",
        llm_model="anirvium-text",
        llm_max_tokens=384,
        llm_disable_thinking=True,
    )
    OpenAICompatibleLLMClient(settings).generate([{"role": "user", "content": "Help"}])

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["max_tokens"] == 384
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
