from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from constants.agent_names import AgentNames
from models.requirement_intelligence import RequirementIntelligence


class RequirementIntelligenceService:

    def __init__(self,ai_service,prompt_builder: PromptBuilder):
        self.ai_service = ai_service
        self.prompt_builder = prompt_builder




    def analyze(self,requirement,clarification_context="",):

        prompt = self.prompt_builder.requirement_intelligence(requirement,clarification_context,)

        request = LLMRequest(system_prompt=prompt.system_prompt,user_prompt=prompt.user_prompt,)

        response = self.ai_service.generate_json(AgentNames.REQUIREMENT_INTELLIGENCE,request,)

        from utils.logger import logger as _log
        _log.info("RequirementIntelligence response keys: %s | intent=%r", list(response.keys()) if isinstance(response, dict) else type(response).__name__, response.get("intent") if isinstance(response, dict) else None)

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

        # Normalise status so the router always receives "READY" or
        # "NEEDS_CLARIFICATION" regardless of what the LLM returns.
        # The model sometimes returns variants like "ready_to_proceed",
        # "ready_for_execution", "needs_clarification_on_scope", etc.
        if isinstance(response.get("status"), str):
            raw_status = response["status"].upper()
            if "CLARIF" in raw_status:
                response["status"] = "NEEDS_CLARIFICATION"
            else:
                # Any "READY*" variant (READY, READY_TO_PROCEED, etc.) → READY
                response["status"] = "READY"

        if (
            response.get("status") == "NEEDS_CLARIFICATION"
            and not filtered_questions
        ):
            response["status"] = "READY"

        raw_intent = (
            response.get("intent")
            or response.get("goal")
            or response.get("workflow_type")
            or response.get("requirement_type")
            or ""
        )

        return RequirementIntelligence(
            status=response.get(
                "status",
                "READY"
            ),
            intent=raw_intent,
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