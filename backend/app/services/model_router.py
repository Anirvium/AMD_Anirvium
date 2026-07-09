from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.config import Settings, get_settings


class ModelRole(str, Enum):
    TEXT_AGENT = "text_agent"
    CRITIC_AGENT = "critic_agent"
    EMBEDDING = "embedding"
    RERANKER = "reranker"


@dataclass(frozen=True)
class ModelRoute:
    role: ModelRole
    model_name: str
    provider: str
    base_url: str
    runtime_profile: str


class ModelRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def route(self, role: ModelRole) -> ModelRoute:
        return ModelRoute(
            role=role,
            model_name=self._model_for_role(role),
            provider=self.settings.llm_provider,
            base_url=self.settings.llm_base_url,
            runtime_profile=self.settings.amd_runtime_profile,
        )

    def _model_for_role(self, role: ModelRole) -> str:
        if role == ModelRole.CRITIC_AGENT:
            return self.settings.llm_critic_model
        if role == ModelRole.EMBEDDING:
            return self.settings.llm_embedding_model
        if role == ModelRole.RERANKER:
            return self.settings.llm_reranker_model
        if self.settings.llm_model and self.settings.llm_model != "mock-trajectory-model":
            return self.settings.llm_model
        return self.settings.llm_text_model


def build_model_router() -> ModelRouter:
    return ModelRouter()
