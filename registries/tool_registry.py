from services.functional_service import FunctionalCasesGenerator
from registries.base_registry import BaseRegistry



class ToolRegistry(BaseRegistry):

   def __init__(self,llm_service):

        super().__init__()
        
        self.llm_service = llm_service     

        self._register_default_tools()
        
        
   
   
   
   def _register_default_tools(self):

    self.register("testcase", FunctionalCasesGenerator(self.llm_service))
    
        
            