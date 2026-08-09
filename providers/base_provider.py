from abc import ABC, abstractmethod
from typing import Any

from ai.models.llm_request import LLMRequest
from ai.models.llm_response import LLMResponse
from ai.profiles.agent_profile import AgentProfile


class BaseProvider(ABC):
    """
    Base contract for all LLM providers.

    Every provider receives the standardized LLMRequest and
    AgentProfile and must return the standardized LLMResponse.

    Provider-specific details such as API clients, authentication,
    token extraction, and response conversion remain inside the
    concrete provider implementation.
    """

    @abstractmethod
    def generate(self,request: LLMRequest,profile: AgentProfile) -> LLMResponse:
        """
        Generate an LLM response.

        Args:
            request: Standardized system and user prompt payload.
            profile: Agent-specific model and generation configuration.

        Returns:
            Standardized LLMResponse containing generated content,
            model information, provider information, and token usage.
        """
        raise NotImplementedError