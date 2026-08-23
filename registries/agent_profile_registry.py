from ai.profiles.agent_profile import AgentProfile
from config import LLM_PROVIDER, MODEL_NAME
from constants.agent_names import AgentNames
from registries.base_registry import BaseRegistry

# Sensible default model per provider, used when MODEL_NAME is not set.
_PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "groq":       "llama-3.3-70b-versatile",
    "ollama":     "llama3.2",
    "claude_cli": "claude-sonnet-4-6",
}

# Legacy fallback — preserved so existing .env files that point to Groq
# and still work with the old model name don't break.
_LEGACY_DEFAULT = "openai/gpt-oss-120b"


def _resolve_model() -> str:
    """
    Return the model name to use for all agent profiles.

    Priority: MODEL_NAME env var > provider default > legacy fallback.
    """
    if MODEL_NAME:
        return MODEL_NAME
    return _PROVIDER_DEFAULT_MODELS.get(LLM_PROVIDER, _LEGACY_DEFAULT)


class AgentProfileRegistry(BaseRegistry[AgentProfile]):
    """
    Maintains all Agent Profiles.

    The active model is resolved once at construction time from:
      1. MODEL_NAME env var (explicit override)
      2. Provider-specific default for LLM_PROVIDER
    """

    def __init__(self):
        super().__init__()
        self._register_default_profiles()

    def _register_default_profiles(self):
        model = _resolve_model()

        self.register(
            AgentNames.REQUIREMENT_INTELLIGENCE,
            AgentProfile(
                agent_name=AgentNames.REQUIREMENT_INTELLIGENCE,
                model=model,
                temperature=0.1,
                response_format="json",
                max_output_tokens=2000,
            ),
        )

        self.register(
            AgentNames.PLANNER,
            AgentProfile(
                agent_name=AgentNames.PLANNER,
                model=model,
                temperature=0.2,
                response_format="json",
                max_output_tokens=1200,
            ),
        )

        self.register(
            AgentNames.EXECUTION,
            AgentProfile(
                agent_name=AgentNames.EXECUTION,
                model=model,
                temperature=0.2,
                max_output_tokens=2000,
            ),
        )

        self.register(
            AgentNames.REVIEW,
            AgentProfile(
                agent_name=AgentNames.REVIEW,
                model=model,
                temperature=0.1,
                response_format="json",
                max_output_tokens=800,
            ),
        )

        self.register(
            AgentNames.CORRECTION,
            AgentProfile(
                agent_name=AgentNames.CORRECTION,
                model=model,
                temperature=0.2,
                max_output_tokens=2500,
            ),
        )

        self.register(
            AgentNames.SUMMARY,
            AgentProfile(
                agent_name=AgentNames.SUMMARY,
                model=model,
                temperature=0.2,
                max_output_tokens=1000,
            ),
        )

        self.register(
            AgentNames.TESTCASE,
            AgentProfile(
                agent_name=AgentNames.TESTCASE,
                model=model,
                temperature=0.2,
                max_output_tokens=2500,
            ),
        )

        self.register(
            AgentNames.AUTOMATION,
            AgentProfile(
                agent_name=AgentNames.AUTOMATION,
                model=model,
                temperature=0.2,
                max_output_tokens=4000,
            ),
        )

        self.register(
            AgentNames.DATABASE,
            AgentProfile(
                agent_name=AgentNames.DATABASE,
                model=model,
                temperature=0.2,
                max_output_tokens=2500,
            ),
        )