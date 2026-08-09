import os
from groq import Groq
from ai.models.llm_request import LLMRequest
from ai.models.llm_response import LLMResponse
from ai.profiles.agent_profile import AgentProfile
from ai.token.token_usage import TokenUsage
from providers.base_provider import BaseProvider




class  GroqProvider(BaseProvider):
    """
    Groq implementation of the standardized LLM provider contract.

    The provider is responsible only for:
        - communicating with Groq
        - sending the LLMRequest
        - extracting the generated response
        - extracting actual token usage

    Pricing and cost calculation are handled outside the provider.
    """

    def __init__(self):
        self.model = "openai/gpt-oss-120b"



    def generate( self,request: LLMRequest,profile: AgentProfile,)->LLMResponse:
        """
        Generate a response using Groq.

        Args:
            request: Standardized LLM request containing system
                and user prompts.
            profile: Agent-specific model and generation settings.

        Returns:
            Standardized LLMResponse.
        """


        if not isinstance(request, LLMRequest):
            raise TypeError(
                "request must be an instance of LLMRequest."
            )

        if not isinstance(profile, AgentProfile):
            raise TypeError(
                "profile must be an instance of AgentProfile."
            )

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set."
            )

        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model=profile.model,
            temperature=profile.temperature,
            messages=[
                {
                    "role": "system",
                    "content": request.system_prompt,
                },
                {
                    "role": "user",
                    "content": request.user_prompt,
                },
            ],
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError("Groq returned an empty response.")

        usage = response.usage

        token_usage = TokenUsage(
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

        return LLMResponse(
            content=content,
            provider="Groq",
            token_usage=token_usage,
            model=profile.model,
        )