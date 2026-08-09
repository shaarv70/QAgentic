from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from constants.agent_names import AgentNames
from constants.prompt_names import PromptNames
from prompts.requirement_intelligence_prompt import (
    build_requirement_intelligence_prompt
)

from models.requirement_intelligence import RequirementIntelligence


class RequirementIntelligenceService:

    def __init__(self, ai_service,prompt_builder:PromptBuilder):

        self.ai_service = ai_service
        self.prompt_builder = prompt_builder


    def analyze(self,requirement):

        system_prompt, user_prompt =  self.prompt_builder.requirement_intelligence(requirement)

        request =LLMRequest(system_prompt=system_prompt,user_prompt=user_prompt)

        response = self.ai_service.generate_json(AgentNames.REQUIREMENT_INTELLIGENCE,request)



        return RequirementIntelligence(
            status=response["status"],
            intent=response["intent"],
            context=response.get("context", {}),
            assumptions=response.get("assumptions", []),
            questions=response.get("questions", [])
        )