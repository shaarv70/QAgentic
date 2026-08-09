import json
from ai.services.pricing_service import PricingService
from ai.token.token_manager import TokenManager
from ai.models.llm_request import LLMRequest
from ai.models.llm_response import LLMResponse
from registries.agent_profile_registry import AgentProfileRegistry
from config import LLM_PROVIDER
from registries.provider_registry import ProviderRegistry
from utils.logger import logger


class AIService:


    def __init__(self,provider_registry: ProviderRegistry,profile_registry:AgentProfileRegistry,token_manager,pricing_service: PricingService,):

        self.provider_registry = provider_registry
        self.profile_registry = profile_registry
        self.token_manager =token_manager
        self.pricing_service = pricing_service


  
    def generate(self,agent_name: str,request: LLMRequest) -> LLMResponse:

        profile = self.profile_registry.get(agent_name)

        input_tokens = self.token_manager.estimate_prompt_tokens(request.system_prompt,request.user_prompt,)

        logger.info("LLM request | agent=%s | estimated_input_tokens=%d",agent_name,input_tokens,)

        provider = self.provider_registry.get(LLM_PROVIDER)

        response= provider.generate(request=request,profile=profile)

        if response.token_usage:
            usage = response.token_usage
            response.cost = self.pricing_service.calculate(model=response.model,input_tokens=usage.input_tokens,output_tokens=usage.output_tokens,)
            logger.info("LLM cost | agent=%s | model=%s | ""input_cost=$%.8f | output_cost=$%.8f | total_cost=$%.8f",
            agent_name,
            response.model,
            response.cost.input_cost,
            response.cost.output_cost,
            response.cost.total_cost,
        )

        return response



    def generate_json(self,agent_name: str,request: LLMRequest) -> dict:

        response = self.generate(agent_name,request)

        try:
            return json.loads(response.content)

        except json.JSONDecodeError as ex:
            raise ValueError(
                f"Invalid JSON returned by LLM:\n{response.content}"
            ) from ex



