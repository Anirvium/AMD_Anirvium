from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    llm_provider: str = "mock"
    llm_base_url: str = "http://localhost:8001/v1"
    llm_api_key: str = ""
    llm_model: str = "mock-trajectory-model"
    llm_text_model: str = "Qwen/Qwen3-30B-A3B-Instruct-2507"
    llm_critic_model: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
    llm_embedding_model: str = "Qwen/Qwen3-Embedding-4B"
    llm_reranker_model: str = "Qwen/Qwen3-Reranker-4B"
    llm_timeout_seconds: int = 60

    vector_backend: str = "local"
    vector_base_url: str = "http://localhost:6333"
    vector_kb_collection: str = "anirvium_kb"
    vector_memory_collection: str = "anirvium_memory"
    vector_trajectory_collection: str = "anirvium_trajectories"
    vector_dimension: int = 64

    memory_backend: str = "local"
    redis_url: str = "redis://localhost:6379/0"
    short_term_memory_ttl_seconds: int = 3600
    mid_term_memory_limit: int = 50

    amd_provider_name: str = "AMD Developer Cloud"
    amd_backend_name: str = "vLLM/ROCm"
    amd_gpu_name: str = "AMD Instinct MI300X 192GB"
    amd_runtime_profile: str = "text"

    run_store_dir: str = Field(default="app/data/runs")

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
