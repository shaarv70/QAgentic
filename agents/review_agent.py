from agents.base_agent import BaseAgent
from utils.logger import logger

class ReviewAgent(BaseAgent): 
     
     
     def __init__(self,review_service):
          
          self.review_service=review_service
    
     
     def execute(self, state):

            for artifact_name in state.artifacts:

                 review_result = self.review_service.review(state.artifacts[artifact_name])
                 logger.info(review_result["feedback"])
                 state.artifacts[artifact_name] = review_result
            return state