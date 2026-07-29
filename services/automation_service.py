from prompts.automation_prompt import build_automation_prompt
from prompts.correction_prompt import build_correction_prompt
from services.base_generator import BaseGenerator


class AutomationGenerator(BaseGenerator):
    
    

    def __init__(self, llm_service):
        
        self.llm_service = llm_service


    def generate(self, task, execution_context):

        prompt = build_automation_prompt(
            task=task,
            requirement=execution_context.requirement,
            dependency_artifacts=execution_context.dependency_artifacts
        )

        return self.llm_service.ask_llm(prompt)


    def correct(
        self,
        task,
        execution_context,
        previous_content,
        feedback
    ):

        prompt = build_correction_prompt(
            task=task,
            requirement=execution_context.requirement,
            previous_content=previous_content,
            feedback=feedback,
            dependency_artifacts=execution_context.dependency_artifacts
        )

        return self.llm_service.ask_llm(prompt)