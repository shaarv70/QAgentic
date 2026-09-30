import asyncio

from capabilities.base_capability import BaseCapability
from domain.repository.repository_operation import (
    RepositoryOperation,
    RepositoryOperationType,
)
from models.capability_result import CapabilityResult



class RepositoryCapability(BaseCapability):

    def __init__(self, repository_provider):
        self.repository_provider = repository_provider

    @property
    def name(self) -> str:
        return "repository"

    def execute(
        self,
        task,
        context=None,
    ) -> CapabilityResult:

        try:
            operation = self._build_operation(task)

            repository = self._build_repository_context(
                task=task,
                context=context,
            )

            workflow_state = (
                getattr(
                    context,
                    "workflow_state",
                    None,
                )
                if context is not None
                else None
            )

            result = asyncio.run(
                self.repository_provider.execute(
                    operation=operation,
                    repository=repository,
                    workflow_state=workflow_state,
                )
            )

            if (
                isinstance(result, dict)
                and result.get("status")
                == "APPROVAL_REQUIRED"
            ):
                return CapabilityResult(
                    status="PENDING_APPROVAL",
                    data=result,
                    error=result.get("reason"),
                    retryable=False,
                )

            if (
                isinstance(result, dict)
                and result.get("status")
                == "REJECTED"
            ):
                return CapabilityResult(
                    status="FAILED",
                    data=result,
                    error=(
                        result.get("reason")
                        or "Repository operation was rejected."
                    ),
                    retryable=False,
                )

            return CapabilityResult(
                status="PASSED",
                data=result,
                error=None,
            )

        except (TypeError, ValueError) as exc:

            return CapabilityResult(
                status="FAILED",
                data=None,
                error=str(exc),
                retryable=False,
            )

        except Exception as exc:

            return CapabilityResult(
                status="FAILED",
                data=None,
                error=str(exc),
                retryable=True,
            )

    def _build_operation(self, task) -> RepositoryOperation:

        context = task.context or {}

        operation_value = context.get("operation")

        if operation_value is None:
            raise ValueError(
                "Repository task is missing 'operation'."
            )

        try:
            operation_type = RepositoryOperationType(
                operation_value
            )
        except ValueError as exc:
            raise ValueError(
                f"Unsupported repository operation: "
                f"{operation_value}"
            ) from exc

        arguments = context.get(
            "arguments",
            {},
        )

        if not isinstance(arguments, dict):
            raise TypeError(
                "Repository operation arguments "
                "must be a dictionary."
            )

        return RepositoryOperation(
            operation=operation_type,
            arguments=arguments,
        )

    def _build_repository_context(
        self,
        task,
        context=None,
    ) -> dict:

        task_context = task.context or {}

        repository = task_context.get(
            "repository"
        )

        if repository is None:
            raise ValueError(
                "Repository task is missing "
                "'repository' context."
            )

        if not isinstance(repository, dict):
            raise TypeError(
                "Repository context must be a dictionary."
            )

        return repository