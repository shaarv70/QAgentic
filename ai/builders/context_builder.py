import json
from dataclasses import asdict, fields, is_dataclass

from memory.memory_manager import MemoryManager
from memory.models.memory_context import MemoryContext
from memory.models.memory_query import MemoryQuery


class ContextBuilder:
    """
    ==========================================================
    Context Builder
    ==========================================================

    Centralizes runtime information supplied to prompts.

    Responsibilities:
        - Normalize domain objects
        - Serialize structured context
        - Keep serialization logic outside prompt files
    """

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
    ):
        self.memory_manager = memory_manager



    @staticmethod
    def _serialize(value) -> str:
        """
        Convert runtime values into prompt-safe text.

        Handles:
            - strings
            - dictionaries
            - lists
            - dataclasses
            - Pydantic models
            - domain objects
            - nested non-JSON objects
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        return json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            default=ContextBuilder._serialize_object,
        )





    @staticmethod
    def _serialize_object(value):
        """
        Convert an object that JSON does not understand into a
        JSON-compatible representation.
        """

        # Dataclass instance, including @dataclass(slots=True)
        if not isinstance(value, type) and is_dataclass(value):
            return {
                field.name: getattr(value, field.name)
                for field in fields(value)
            }

        # Pydantic v2
        if hasattr(value, "model_dump"):
            return value.model_dump()

        # Pydantic v1 / legacy models
        if hasattr(value, "dict"):
            return value.dict()

        # Normal Python objects
        if hasattr(value, "__dict__"):
            return vars(value)

        # Final safe representation
        return str(value)



    @staticmethod
    def task(task) -> str:
        """
        Convert a Task into a stable JSON representation.
        """

        return ContextBuilder._serialize(
            {
                "task_id": task.task_id,
                "capability": task.capability,
                "description": task.description,
                "context": task.context,
                "depends_on": task.depends_on,
            }
        )

    @staticmethod
    def artifact(artifact) -> str:
        """
        Convert a generated Artifact into prompt-ready context.

        The centralized serializer is deliberately used here
        because artifact.content may contain nested runtime
        objects such as execution results or execution plans.
        """

        return ContextBuilder._serialize(
            {
                "task_id": artifact.task_id,
                "capability": artifact.capability,
                "content": artifact.content,
            }
        )

    @staticmethod
    def requirement(requirement) -> str:
        """
        Normalize requirement or other structured domain context.
        """

        return ContextBuilder._serialize(requirement)

    @staticmethod
    def artifacts(artifacts) -> str:
        """
        Serialize dependency artifacts for prompt consumption.
        """

        if not artifacts:
            return "{}"

        return ContextBuilder._serialize(artifacts)

    def build_memory_context(
        self,
        query: MemoryQuery,
    ) -> MemoryContext:

        if self.memory_manager is None:
            return MemoryContext()

        memories = self.memory_manager.retrieve(query)

        return MemoryContext(
            memories=memories
        )

    @staticmethod
    def memory(
        memory_context: MemoryContext,
    ) -> str:

        if memory_context.is_empty:
            return ""

        return "\n".join(
            memory.content
            for memory in memory_context.memories
        )

