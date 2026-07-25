from agents.base_agent import BaseAgent
from concurrent.futures import ThreadPoolExecutor
from config import MAX_RETRIES
from utils.logger import logger
import time


class ExecutionAgent(BaseAgent):
    
    
    def __init__(self,tool_registry):
        
        super().__init__()
        self.tool_registry=tool_registry
       
    

    def execute(self, state):
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures=[]   
            
            for artifact in state.plan.artifacts:
                    future = executor.submit(self.generate_artifact,artifact,state)   #submit(function, *args)
                    futures.append(future)

            for future in futures:
                
                artifact_name,result = future.result()
                try:
                    state.artifacts[artifact_name] = result
                except Exception:
                    logger.exception(f"{artifact_name} Generator Failed")
        return state

    
    
    def generate_artifact(self, artifact, state):
        start=time.perf_counter()
        generator = self.tool_registry.get(artifact)
        logger.info(f"Started generating {artifact}")
        for attempt in range(MAX_RETRIES):
            try:
                result= generator.generate(state.application_type,state.requirement)
                end=time.perf_counter()
                logger.info(f"{artifact} completed in {end-start:.2f} sec")
                return artifact,result
            except Exception as e:
                logger.exception(e)
                logger.warning(f"{artifact} Retry {attempt + 1}")
                
        raise Exception(f"{artifact} failed after 3 retries")        