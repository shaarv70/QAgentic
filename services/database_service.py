from constants.agent_names import AgentNames
from models.action_spec import ActionSpec
from services.base_generator import BaseGenerator


class DatabaseGenerator(BaseGenerator):

    action_spec = ActionSpec(
        name="database",
        kind="tool",
        description="Generate database validation or test artifacts.",
        requires=("requirement",),
        produces=("database_artifact",),
    )

    def __init__(self, ai_service, prompt_builder):
        super().__init__(
            ai_service,
            prompt_builder,
        )

    def generate(self, task, execution_context):
        prompt = self.prompt_builder.database(
            task,
            execution_context.requirement,
        )

        return self.generate_text(
            AgentNames.DATABASE,
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