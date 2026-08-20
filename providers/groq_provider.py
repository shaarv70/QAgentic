import os
from groq import Groq
from ai.exceptions.ai_exception import AIRateLimitError
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
        try:
            response = client.chat.completions.create(
            model=profile.model,
            temperature=profile.temperature,
            max_tokens=profile.max_output_tokens,
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
        except Exception as ex:
            if getattr(ex, "status_code", None) == 429:
                retry_after = None

                response = getattr(ex, "response", None)

                if response is not None:
                    headers = getattr(response, "headers", {})

                    retry_value = headers.get("retry-after")

                    if retry_value:
                        try:
                            retry_after = float(retry_value)
                        except (TypeError, ValueError):
                            retry_after = None

                raise AIRateLimitError(
                    "LLM provider rate limit exceeded.",
                    retry_after=retry_after,
                ) from ex

            raise

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