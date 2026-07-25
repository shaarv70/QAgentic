from prompts.review_prompt import build_review_prompt
import json

class ReviewService:
     
     def __init__(self,llm_service):
          self.llm_service=llm_service
          
     

     def review(self,content):
          
          prompt=build_review_prompt(content)
          response= self.llm_service.ask_llm(prompt)
          return response