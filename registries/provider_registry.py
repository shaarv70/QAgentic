from providers.base_provider import BaseProvider
from providers.groq_provider import GroqProvider
from registries.base_registry import BaseRegistry
from providers.ollama_provider import OllamaProvider


class ProviderRegistry(BaseRegistry[BaseProvider]):


    def __init__(self):
        super().__init__()
        self._register_default_providers()





    def _register_default_providers(self):

        self.register("ollama", OllamaProvider())
        self.register("groq",GroqProvider())





