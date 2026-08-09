from dataclasses import dataclass


@dataclass(slots=True)
class TokenUsage:
    """
    Represents token consumption for a single LLM request.

    This model keeps token accounting independent from:
        - providers
        - agents
        - prompt builders
        - logging
    """

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Return total input + output tokens."""
        return self.input_tokens + self.output_tokens