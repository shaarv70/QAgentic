from providers.base_provider import BaseProvider
from providers.claude_cli_provider import ClaudeCLIProvider
from providers.groq_provider import GroqProvider
from providers.ollama_provider import OllamaProvider
from registries.base_registry import BaseRegistry


class ProviderRegistry(BaseRegistry[BaseProvider]):

    def __init__(self):
        super().__init__()
        self._register_default_providers()

    def _register_default_providers(self):
        self.register("ollama",     OllamaProvider())
        self.register("groq",       GroqProvider())
        self.register("claude_cli", ClaudeCLIProvider())