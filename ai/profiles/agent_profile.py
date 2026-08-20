from dataclasses import dataclass


@dataclass(slots=True)
class AgentProfile:
    """
    ==========================================================
    Class : AgentProfile

    Purpose:
        Stores the default AI configuration
        for an Agent.
    ==========================================================
    """

    agent_name: str

    model: str

    temperature: float = 0.2

    response_format: str = "text"

    max_output_tokens: int = 2048