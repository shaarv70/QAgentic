class AIProviderError(Exception):
    """Base exception for provider-related failures."""


class AIRateLimitError(AIProviderError):
    """Raised when an LLM provider rate-limits a request."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after