import json


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

    Future:
        - RAG context
        - Repository context
        - Execution memory
        - Previous attempts
        - Retrieved documents
    ==========================================================
    """

    @staticmethod
    def _serialize(value) -> str:
        """
        Convert runtime values into prompt-safe text.

        Handles:
            - strings
            - dictionaries
            - lists
            - domain objects
            - nested non-JSON objects

        Serialization remains centralized here so prompt files
        do not need to know how application objects are represented.
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

        if hasattr(value, "model_dump"):
            return value.model_dump()

        if hasattr(value, "dict"):
            return value.dict()

        if hasattr(value, "__dict__"):
            return vars(value)

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
        """

        return json.dumps(
            {
            "task_id": artifact.task_id,
            "capability": artifact.capability,
            "content": artifact.content,
            },
            indent=2,
            ensure_ascii=False,)

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