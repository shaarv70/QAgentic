from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)  #Python internally created dict within an object, so this will skip that dict hence less memory, faster atttribute access, prevents adding random atttribute accidently
class LLMRequest:
    """
    ==========================================================
    Class : LLMRequest

    Purpose:
        Represents a standardized request sent to any
        Large Language Model provider.

    Responsibilities:
        • Store prompt information.
        • Store model configuration.
        • Carry provider-independent metadata.

    This model is provider agnostic and is shared across
    Groq, Ollama and Gemini implementations.

    Future versions may extend this model with:
        - Memory
        - Context
        - Guardrails
        - Tool Calling
        - MCP
    ==========================================================
    """

    system_prompt: str

    user_prompt: str

    metadata: dict[str, Any] = field(default_factory=dict)   # Whenever a new object is created, create a NEW empty dictionary.