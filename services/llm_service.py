import json

class LLMService:
    
    
    def __init__(self, provider_registry):
        self.provider_registry = provider_registry

    
    
    def ask_llm(self, prompt):

        provider = self.provider_registry.get("ollama")   ##return Ollama provider object

        response= provider.generate(prompt).strip()
        try: 
            return json.loads(response)
        except json.JSONDecodeError:
            return response

   
   
