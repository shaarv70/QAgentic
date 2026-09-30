from ai.models.llm_request import LLMRequest
from constants.agent_names import AgentNames
from models.review import Review


class ReviewService:

    def __init__(
        self,
        ai_service,
        prompt_builder,
    ):
        self.ai_service = ai_service
        self.prompt_builder = prompt_builder

    def review(
        self,
        task,
        artifact,
        dependency_artifacts=None,
    ):

        system_prompt, user_prompt = (
            self.prompt_builder.review(
                task,
                artifact,
                dependency_artifacts or {},
            )
        )

        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        response = self.ai_service.generate_json(
            AgentNames.REVIEW,
            request,
        )

        status = response["status"].upper()

        if status not in ["PASS", "FAIL"]:
            raise ValueError(
                f"Invalid review status: {status}"
            )

        return Review(
            status=status,
            feedback=response.get("feedback", ""),
        )