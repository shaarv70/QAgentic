from abc import ABC, abstractmethod
import time

from utils.logger import logger


class BaseAgent(ABC):

    def run(self, state):

        agent_name = self.__class__.__name__
        start = time.perf_counter()
        logger.info(f"{agent_name} Started")

        try:

            state = self.execute(state)
            logger.info(f"{agent_name} Completed")

            return state

        except Exception:

            logger.exception(f"{agent_name} Failed")

            raise

        finally:

            execution_time = (time.perf_counter() - start)

            logger.info(f"Execution Time : "f"{execution_time:.2f} seconds")


   
    @abstractmethod
    def execute(self, state):
        pass