from registries.base_registry import BaseRegistry
from services.automation_service import AutomationGenerator
from services.base_generator import BaseGenerator
from services.database_service import DatabaseGenerator
from services.summary_service import SummaryGenerator
from services.testcase_service import TestCaseGenerator



class ToolRegistry(BaseRegistry[BaseGenerator]):



   def __init__(self,ai_service,prompt_builder):

        super().__init__()

        self.ai_service = ai_service
        self.prompt_builder = prompt_builder

        self._register_default_tools()





   def _register_default_tools(self):

        self.register(
            "testcase",
            TestCaseGenerator(self.ai_service,self.prompt_builder,))

        self.register(
            "automation",
            AutomationGenerator(self.ai_service,self.prompt_builder,))

        self.register(
            "database",
            DatabaseGenerator(self.ai_service,self.prompt_builder,))

        self.register(
            "summary",
            SummaryGenerator(self.ai_service,self.prompt_builder,))


