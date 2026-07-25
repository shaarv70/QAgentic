from prompts.testcase_prompt import build_testcase_prompt
from services.base_generator import BaseGenerator


class FunctionalCasesGenerator(BaseGenerator):

    def __init__(self, llm_service):
        self.llm_service = llm_service

    def generate(self, application_type, requirement):

        prompt = build_testcase_prompt(
            application_type,
            requirement
        )

        return self.llm_service.ask_llm(prompt)