from abc import ABC, abstractmethod
from ai.models.llm_request import LLMRequest


class BaseGenerator(ABC):

    """
==========================================================
Base Generator
==========================================================

Purpose:
    Common foundation for all artifact generators.

Every generator receives the same AIService and
PromptBuilder dependencies.

This class also centralizes text generation so individual
generators do not duplicate LLMRequest creation.
==========================================================
"""

    def __init__(self, ai_service,prompt_builder):

        self.ai_service = ai_service
        self.prompt_builder = prompt_builder



    def generate_text(self,agent_name,system_prompt,user_prompt,):

        request = LLMRequest(system_prompt=system_prompt,user_prompt=user_prompt,)

        response = self.ai_service.generate(agent_name,request,)

        return response.content



    @abstractmethod
    def generate(self, task, execution_context):
        pass




    @abstractmethod
    def correct(self,task,execution_context,previous_content,feedback):
        pass