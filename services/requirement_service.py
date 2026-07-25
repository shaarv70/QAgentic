import json
from prompts.requirement_prompt import build_requirement_prompt
from utils.logger import logger


class RequirementService:
    
        def __init__(self,llm_service) -> None:
             
             self.llm_service=llm_service


        def analyze_requirement(self,application_type, requirement):
    
            analysis_prompt=build_requirement_prompt(application_type,requirement)
            logger.info("Thinking...")
            return self.llm_service.ask_llm(analysis_prompt)
           