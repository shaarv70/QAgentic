from agents.base_agent import BaseAgent
from utils.logger import logger

class PlannerAgent(BaseAgent):

        def __init__(self,planning_service):

               super().__init__()
               self.planning_service=planning_service




        def execute(self, state):

             state.plan=self.planning_service.create_plan(state.requirement, state.requirement_intelligence)   ## Store generated Plan object in state
             logger.info( f"Tasks Planned: {[task.capability for task in state.plan.tasks]}")
             return state
    