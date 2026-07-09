from functools import lru_cache

from app.services.agent_runner import AgentRunner


@lru_cache
def get_agent_runner() -> AgentRunner:
    return AgentRunner()

