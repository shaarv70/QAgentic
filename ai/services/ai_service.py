import json
import time
from ai.exceptions.ai_exception import AIRateLimitError
from ai.services.pricing_service import PricingService
from ai.token.token_manager import TokenManager
from ai.models.llm_request import LLMRequest
from ai.models.llm_response import LLMResponse
from registries.agent_profile_registry import AgentProfileRegistry
from config import LLM_PROVIDER
from registries.provider_registry import ProviderRegistry
from utils.logger import logger


class AIService:

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        profile_registry: AgentProfileRegistry,
        token_manager: TokenManager,
        pricing_service: PricingService,
    ):
        self.provider_registry = provider_registry
        self.profile_registry = profile_registry
        self.token_manager = token_manager
        self.pricing_service = pricing_service



    def generate(self,agent_name: str,request: LLMRequest,) -> LLMResponse:

        profile = self.profile_registry.get(agent_name)

        input_tokens = self.token_manager.estimate_prompt_tokens(
            request.system_prompt,
            request.user_prompt,
        )

        logger.info("LLM request | agent=%s | estimated_input_tokens=%d",agent_name,input_tokens,)

        provider = self.provider_registry.get(LLM_PROVIDER)

        response = self._generate_with_retry(provider=provider,request=request,profile=profile,)

        if response.token_usage:
            usage = response.token_usage

            response.cost = self.pricing_service.calculate(
                model=response.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_creation_input_tokens=(usage.cache_creation_input_tokens),
                cache_read_input_tokens=(usage.cache_read_input_tokens),)

            logger.info(
                "LLM cost | agent=%s | model=%s | "
                "input_cost=$%.8f | output_cost=$%.8f | total_cost=$%.8f",
                agent_name,
                response.model,
                response.cost.input_cost,
                response.cost.output_cost,
                response.cost.total_cost,
            )

        return response



    def generate_json(self,agent_name: str,request: LLMRequest,) -> dict:

        response = self.generate(agent_name,request,)

        try:
            return json.loads(response.content)

        except json.JSONDecodeError as ex:
            raise ValueError(
                f"Invalid JSON returned by LLM:\n{response.content}") from ex




    def _generate_with_retry(self,provider,request: LLMRequest,profile,) -> LLMResponse:

        max_attempts = 3

        for attempt in range(max_attempts):

            try:
                return provider.generate(
                    request=request,
                    profile=profile,
                )

            except AIRateLimitError as ex:

                if attempt == max_attempts - 1:
                    raise

                delay = ex.retry_after

                if delay is None:
                    delay = 2 ** attempt

                logger.warning(
                    "LLM rate limit | "
                    "attempt=%d/%d | retry_in=%.2fs",
                    attempt + 1,
                    max_attempts,
                    delay,
                )

                time.sleep(delay)

        raise RuntimeError(
            "LLM generation failed after retry attempts.")