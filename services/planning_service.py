from prompts.planning_prompt import build_planning_prompt 
from models.plan import Plan


class PlanningService   :
     
    def __init__(self,llm_service):
        
        self.llm_service=llm_service
    
    
    def plan_artifacts(self,application_type, requirement):
   
        plan=Plan()
        prompt = build_planning_prompt(application_type,requirement)
        response = self.llm_service.ask_llm(prompt)
        plan.artifacts=response["artifacts"]        #store list of artifacts in plan.artifacts  list
        return plan                                 #returning the object of plan containing list of artifacts 