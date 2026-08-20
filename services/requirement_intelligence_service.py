from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from constants.agent_names import AgentNames
from models.requirement_intelligence import RequirementIntelligence


class RequirementIntelligenceService:

    def __init__(self,ai_service,prompt_builder: PromptBuilder):
        self.ai_service = ai_service
        self.prompt_builder = prompt_builder




    def analyze(self,requirement,clarification_context="",):

        system_prompt, user_prompt = (self.prompt_builder.requirement_intelligence(requirement,clarification_context,))

        request = LLMRequest(system_prompt=system_prompt,user_prompt=user_prompt,)

        response = self.ai_service.generate_json(AgentNames.REQUIREMENT_INTELLIGENCE,request,)

        questions = response.get("questions",[])

        existing_keys = (self._parse_clarification_keys(clarification_context))

        filtered_questions = []

        for question in questions:

            if not isinstance(question, dict):
                continue

            key = question.get("key")
            text = question.get("question")

            if not key or not text:
                continue

            # Never ask an already answered clarification again.
            if key in existing_keys:
                continue

            filtered_questions.append(
                {
                    "key": key,
                    "question": text,
                }
            )

        if (
            response.get("status") == "NEEDS_CLARIFICATION"
            and not filtered_questions
        ):
            response["status"] = "READY"

        return RequirementIntelligence(
            status=response.get(
                "status",
                "READY"
            ),
            intent=response.get(
                "intent",
                ""
            ),
            context=response.get(
                "context",
                {}
            ),
            assumptions=response.get(
                "assumptions",
                []
            ),
            unknowns=response.get(
                "unknowns",
                []
            ),
            questions=filtered_questions,
        )




    @staticmethod
    def _parse_clarification_keys(clarification_context) -> set[str]:

        if not clarification_context:
            return set()

        keys = set()

        for line in clarification_context.splitlines():

            if line.startswith("KEY:"):

                key = line[
                    len("KEY:"):
                ].strip()

                if key:
                    keys.add(key)

        return keys