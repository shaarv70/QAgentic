from constants.agent_names import AgentNames
from models.action_spec import ActionSpec
from services.base_generator import BaseGenerator


class SummaryGenerator(BaseGenerator):

    action_spec = ActionSpec(
        name="summary",
        kind="tool",
        description="Generate a summary from available execution artifacts.",
        requires=(),
        produces=("summary",),
    )

    def __init__(self, ai_service, prompt_builder):
        super().__init__(
            ai_service,
            prompt_builder,
        )

    def generate(self, task, execution_context):
        prompt = self.prompt_builder.summary(
            task,
            execution_context.requirement,
        )

        return self.generate_text(
            AgentNames.SUMMARY,
            prompt.system_prompt,
            prompt.user_prompt,
        )

    def correct(
        self,
        task,
        execution_context,
        previous_content,
        feedback,
    ):
        dependency_artifacts = (
            execution_context.dependency_artifacts
        )

        prompt = self.prompt_builder.correction(
            task,
            execution_context.requirement,
            previous_content,
            feedback,
            dependency_artifacts,
        )

        return self.generate_text(
            AgentNames.CORRECTION,
            prompt.system_prompt,
            prompt.user_prompt,
        )