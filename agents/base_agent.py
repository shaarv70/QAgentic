from abc import ABC, abstractmethod
import time

from utils.logger import logger


class BaseAgent(ABC):

    def run(self, state):

        logger.info(f"{self.__class__.__name__} Started")

        start_time = time.time()

        try:
            state = self.execute(state)
            return state

        except Exception as e:
            logger.exception(e)
            raise

        finally:
            end_time = time.time()

            logger.info(f"{self.__class__.__name__} Completed")
            logger.info(f"Execution Time : {end_time - start_time:.2f} seconds")

    @abstractmethod
    def execute(self, state):
        pass