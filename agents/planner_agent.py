from agents.base_agent import BaseAgent
from utils.logger import logger

class PlannerAgent(BaseAgent):
        
        def __init__(self,planning_service):
               super().__init__()
               self.planning_service=planning_service
        
        def execute(self, state):
                
             state.plan=self.planning_service.plan_artifacts(state.application_type, state.requirement)   #storing oject of plan in state's plan dictionary 
             logger.info(f"Artifacts Selected:{state.plan.artifacts}")
             return state
    