from prompts.requirement_intelligence_prompt import (
    build_requirement_intelligence_prompt
)

from models.requirement_intelligence import RequirementIntelligence


class RequirementIntelligenceService:

    def __init__(self, llm_service):

        self.llm_service = llm_service


    def analyze(self,requirement):

        prompt = build_requirement_intelligence_prompt(requirement)
        response = self.llm_service.ask_llm_json(prompt)

        return RequirementIntelligence(
            status=response["status"],
            intent=response["intent"],
            context=response.get("context", {}),
            assumptions=response.get("assumptions", []),
            questions=response.get("questions", [])
        )