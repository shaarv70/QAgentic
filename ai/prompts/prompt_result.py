from dataclasses import dataclass


@dataclass(slots=True)
class PromptResult:
    """
    Represents the final prompt sent to the LLM.

    Keeping system and user content together gives the
    AI layer a consistent contract while allowing individual
    prompt implementations to evolve independently.
    """

    system_prompt: str
    user_prompt: str

    def __iter__(self):
        """
        Preserve compatibility with existing code such as:

            system_prompt, user_prompt = prompt_result
        """
        yield self.system_prompt
        yield self.user_prompt
