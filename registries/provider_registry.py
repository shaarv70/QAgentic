from providers.gemini_provider import GeminiProvider
from providers.groq_provider import GroqProvider
from registries.base_registry import BaseRegistry
from providers.ollama_provider import OllamaProvider


class ProviderRegistry(BaseRegistry):
    
    
    def __init__(self):
        super().__init__()
        self._register_default_providers()
                
                
    
    def _register_default_providers(self):
        
        self.register("ollama", OllamaProvider())
        self.register("gemini",GeminiProvider())   
        self.register("groq",GroqProvider()) 
          
    
    