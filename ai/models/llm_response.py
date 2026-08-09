from dataclasses import dataclass, field
from typing import Any

from ai.config.llm_cost import LLMCost
from ai.token.token_usage import TokenUsage


@dataclass(slots=True)
class LLMResponse:
    """
    Standard response returned by the AI/provider layer.

    Contains:
        - generated content
        - actual token usage
        - calculated LLM cost
    """

    content: str

    provider: str

    model: str

    token_usage: TokenUsage | None = None

    cost: LLMCost | None = None

    metadata: dict[str, Any] = field(default_factory=dict)