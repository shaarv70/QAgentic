from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from constants.agent_names import AgentNames
from prompts.review_prompt import build_review_prompt
from models.review import Review
import json

class ReviewService:

     def __init__(self,ai_service,prompt_builder:PromptBuilder):

          self.ai_service=ai_service
          self.prompt_builder = prompt_builder


     def review(self,task,artifact):

          system_prompt, user_prompt= self.prompt_builder.review(task,artifact,)


          request = LLMRequest(system_prompt=system_prompt,user_prompt=user_prompt,)

          response = self.ai_service.generate_json(AgentNames.REVIEW,request,)

          status=response["status"].upper()

          if  status not in ["PASS", "FAIL"]:
               raise ValueError(f"Invalid review status: {status}")

          return Review(status=status,feedback=response.get("feedback", ""))
