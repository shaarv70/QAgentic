from registries.base_registry import BaseRegistry
from services.automation_service import AutomationGenerator
from services.database_service import DatabaseGenerator
from services.summary_service import SummaryGenerator
from services.testcase_service import TestCaseGenerator



class ToolRegistry(BaseRegistry):

   def __init__(self,llm_service):

        super().__init__()
        
        self.llm_service = llm_service     

        self._register_default_tools()
        
        
   
   
   
   def _register_default_tools(self):

        self.register(
            "testcase",
            TestCaseGenerator(self.llm_service)
        )

        self.register(
            "automation",
            AutomationGenerator(self.llm_service)
        )

        self.register(
            "database",
            DatabaseGenerator(self.llm_service)
        )

        self.register(
            "summary",
            SummaryGenerator(self.llm_service)
        )
    
        
            