from __future__ import annotations

from app.agents.response_agent import ResponseDraftingAgent
from app.services.llm_client import LLMResponse, strip_private_reasoning


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
