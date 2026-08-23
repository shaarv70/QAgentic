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

    The cache token fields are primarily used by providers such as
    Claude CLI that expose prompt-cache token consumption separately
    from normal input tokens.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Return total input, cache, and output tokens."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )