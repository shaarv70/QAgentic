import json

from config import LLM_PROVIDER

class LLMService:
    
    
    def __init__(self, provider_registry):
        self.provider_registry = provider_registry

    
    
    def ask_llm(self, prompt):

        provider = self.provider_registry.get(LLM_PROVIDER)

        return provider.generate(prompt).strip()


    def ask_llm_json(self, prompt):

       
        response = self.ask_llm(prompt)

        try:
            return json.loads(response)

        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON:\n{response}") from e

   
   
