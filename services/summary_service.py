from ai.builders.prompt_builder import PromptBuilder
from constants.agent_names import AgentNames
from prompts.correction_prompt import build_correction_prompt
from services.base_generator import BaseGenerator
from prompts.summary_prompt import build_summary_prompt


class SummaryGenerator(BaseGenerator):

    def __init__(self, ai_service,prompt_builder:PromptBuilder):

        super().__init__(ai_service,prompt_builder)



    def generate(self, task,  execution_context):

        system_prompt, user_prompt =  self.prompt_builder.summary(task,execution_context.requirement,)

        return self.generate_text(AgentNames.SUMMARY,system_prompt,user_prompt,)



    def correct(self,task,execution_context,previous_content,feedback):

            system_prompt, user_prompt = self.prompt_builder.correction(
            task=task,
            requirement=execution_context.requirement,
            previous_content=previous_content,
            feedback=feedback,
            dependency_artifacts=execution_context.dependency_artifacts,
            )

            return self.generate_text(AgentNames.CORRECTION,system_prompt,user_prompt,)