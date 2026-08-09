from dataclasses import dataclass


@dataclass(slots=True)
class PromptTemplate:

    name: str

    system_prompt: str

    user_prompt: str

    version: str = "1.0"