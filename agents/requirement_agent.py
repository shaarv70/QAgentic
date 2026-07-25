from agents.base_agent import BaseAgent
from services.requirement_service import RequirementService


class RequirementAgent(BaseAgent):
    
    
    def __init__(self,requirement_service) -> None:
       
        super().__init__()
        self.requirement_service=requirement_service
    
    
    def execute(self,state):
        
       state.requirement_analysis=self.requirement_service.analyze_requirement(state.application_type,state.requirement)
       return state