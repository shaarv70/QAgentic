from prompts.review_prompt import build_review_prompt
from models.review import Review
import json

class ReviewService:
     
     def __init__(self,llm_service):
          self.llm_service=llm_service
          
     

     def review(self,task,artifact):
          
          prompt=build_review_prompt(task,artifact)
          response= self.llm_service.ask_llm_json(prompt)
          status=response["status"].upper()
            
          if  status not in ["PASS", "FAIL"]:
               raise ValueError(f"Invalid review status: {status}")
          
          return Review(status=status,feedback=response.get("feedback", "")
)
        