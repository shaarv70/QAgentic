import json

import requests

from ai.models.llm_request import LLMRequest
from ai.models.llm_response import LLMResponse
from ai.profiles.agent_profile import AgentProfile
from ai.token.token_usage import TokenUsage

from config import OLLAMA_URL, MAX_EXECUTION_RETRIES
from providers.base_provider import BaseProvider
from utils.logger import logger


class OllamaProvider(BaseProvider):
    """
    Ollama implementation of the standardized provider contract.

    The provider is responsible for communicating with Ollama and
    converting the provider response into the common LLMResponse model.
    """

    def generate(self,request: LLMRequest,profile: AgentProfile,) -> LLMResponse:
        """
        Generate an LLM response using Ollama.
        """

        if not isinstance(request, LLMRequest):
            raise TypeError(
                "request must be an instance of LLMRequest."
            )

        if not isinstance(profile, AgentProfile):
            raise TypeError(
                "profile must be an instance of AgentProfile."
            )

        payload = {
            "model": profile.model,
            "system": request.system_prompt,
            "prompt": request.user_prompt,
            "stream": False,
            "options": {
                "temperature": profile.temperature,
            },
        }

        for attempt in range(MAX_EXECUTION_RETRIES):
            try:
                response = requests.post(
                    OLLAMA_URL,
                    json=payload,
                )

                if response.status_code != 200:
                    logger.error(
                        "Ollama request failed | attempt=%d | "
                        "status_code=%d",
                        attempt + 1,
                        response.status_code,
                    )
                    continue

                result = response.json()

                content = result.get("response")

                if not content:
                    raise RuntimeError(
                        "Ollama returned an empty response."
                    )

                token_usage = TokenUsage(input_tokens=result.get("prompt_eval_count",0,),output_tokens=result.get("eval_count",0,),)

                return LLMResponse(
                    content=content,
                    provider="Ollama",
                    model=profile.model,
                    token_usage=token_usage,
                )

            except json.JSONDecodeError as exc:
                logger.error("Ollama returned invalid JSON | ""attempt=%d | error=%s",attempt + 1,exc,)

            except requests.RequestException as exc:
                logger.error("Ollama request failed | ""attempt=%d | error=%s",attempt + 1,exc,)

            except Exception as exc:
                logger.error("Ollama generation failed | ""attempt=%d | error=%s",attempt + 1,exc,)

        raise RuntimeError(
            f"Failed to get response from Ollama after "
            f"{MAX_EXECUTION_RETRIES} attempts.")