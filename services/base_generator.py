from abc import ABC, abstractmethod


class BaseGenerator(ABC):

    @abstractmethod
    def generate(self, task, execution_context):
        pass

    @abstractmethod
    def correct(
        self,
        task,
        execution_context,
        previous_content,
        feedback
    ):
        pass