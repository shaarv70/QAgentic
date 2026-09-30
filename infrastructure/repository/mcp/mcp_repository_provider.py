from typing import Any

from capabilities.repository.ports.repository_provider import (
    RepositoryProvider,
)

from domain.repository.repository_execution_checkpoint import (
    RepositoryExecutionCheckpoint,
)

from domain.repository.repository_execution_plan import (
    RepositoryExecutionPlan,
)

from models.approval_model import (
    ApprovalRequest,
    ApprovalStatus,
)


class MCPRepositoryProvider(RepositoryProvider):
    """
    Repository provider backed by MCP.

    Provider-agnostic:
        GitHub / GitLab / Bitbucket / Azure DevOps /
        any other MCP-backed repository provider.

    Responsibilities:

        Repository operation
                ↓
        Repository Execution Agent
                ↓
        Execution Plan
                ↓
        Approval boundary
                ↓
        MCP tool execution
    """

    def __init__(
        self,
        mcp_tool_executor,
        repository_agent,
        approval_service,
    ) -> None:

        self.mcp_tool_executor = mcp_tool_executor
        self.repository_agent = repository_agent
        self.approval_service = approval_service

    async def execute(
        self,
        operation: Any,
        repository: dict[str, Any],
        workflow_state: Any = None,
    ) -> Any:

        server_name = repository.get("mcp_server")

        if not server_name:
            raise ValueError(
                "Repository MCP execution requires "
                "'mcp_server'."
            )

        # ==========================================================
        # 1. LOAD CHECKPOINT
        # ==========================================================

        checkpoint = self._get_checkpoint(
            workflow_state=workflow_state,
        )

        # ==========================================================
        # 2. FIRST EXECUTION
        # ==========================================================

        if checkpoint is None:

            available_tools = (
                await self.mcp_tool_executor.discover_server_tools(
                    server_name
                )
            )

            if not available_tools:
                raise RuntimeError(
                    f"No MCP tools were discovered on "
                    f"repository server '{server_name}'."
                )

            repository_context = {
                "operation": operation.operation.value,
                "arguments": operation.arguments,
                "repository": repository,
            }

            # IMPORTANT:
            # RepositoryExecutionAgent can return
            # RepositoryExecutionPlan | None.
            #
            # Therefore do NOT annotate the assignment directly
            # as RepositoryExecutionPlan.

            generated_plan = self.repository_agent.execute(
                {
                    "repository_operation": operation,
                    "repository_context": repository_context,
                    "available_tools": available_tools,
                }
            )

            if generated_plan is None:
                raise RuntimeError(
                    "RepositoryAgent returned "
                    "no execution plan."
                )

            # Pylance now knows this is non-optional.
            plan: RepositoryExecutionPlan = generated_plan

            if not plan.executable:
                raise RuntimeError(
                    plan.reason
                    or "Repository operation "
                    "is not supported."
                )

            if not plan.operations:
                raise RuntimeError(
                    "Repository execution plan "
                    "contains no operations."
                )

            checkpoint = RepositoryExecutionCheckpoint(
                plan_id=plan.plan_id,
                plan=plan,
                current_operation_index=0,
            )

            self._save_checkpoint(
                workflow_state=workflow_state,
                checkpoint=checkpoint,
            )

        # ==========================================================
        # 3. RESUME
        # ==========================================================

        else:

            checkpoint_plan = checkpoint.plan

            if checkpoint_plan is None:
                raise RuntimeError(
                    "Repository execution checkpoint "
                    "does not contain an execution plan."
                )

            # Pylance now narrows the type correctly.
            plan: RepositoryExecutionPlan = checkpoint_plan

            if checkpoint.completed:
                return {
                    "status": "COMPLETED",
                    "plan_id": checkpoint.plan_id,
                    "results": checkpoint.results,
                }

            if checkpoint.rejected:
                return {
                    "status": "REJECTED",
                    "plan_id": checkpoint.plan_id,
                    "operation_index": (
                        checkpoint.current_operation_index
                    ),
                    "reason": (
                        checkpoint.rejection_reason
                        or "Repository operation "
                        "was rejected."
                    ),
                    "results": checkpoint.results,
                }

        # ==========================================================
        # 4. EXECUTE PLAN SEQUENTIALLY
        # ==========================================================

        while (
            checkpoint.current_operation_index
            < len(plan.operations)
        ):

            operation_index = (
                checkpoint.current_operation_index
            )

            planned_operation = plan.operations[
                operation_index
            ]

            resolved_arguments = (
                self._resolve_result_references(
                    planned_operation.arguments,
                    checkpoint.results,
                )
            )

            # ======================================================
            # APPROVAL BOUNDARY
            # ======================================================

            if planned_operation.requires_approval:

                approval_request_id = (
                    checkpoint.pending_approval_request_id
                )

                # --------------------------------------------------
                # First time reaching this operation.
                # --------------------------------------------------

                if approval_request_id is None:

                    approval_request = (
                        await self.approval_service.create_request(
                            self._build_approval_request(
                                plan=plan,
                                planned_operation=(
                                    planned_operation
                                ),
                                operation_index=(
                                    operation_index
                                ),
                                arguments=(
                                    resolved_arguments
                                ),
                            )
                        )
                    )

                    checkpoint.pending_approval_request_id = (
                        approval_request.request_id
                    )

                    self._save_checkpoint(
                        workflow_state=workflow_state,
                        checkpoint=checkpoint,
                    )

                    return {
                        "status": "APPROVAL_REQUIRED",
                        "plan_id": checkpoint.plan_id,
                        "operation_index": operation_index,
                        "approval_request": approval_request,
                        "results": checkpoint.results,
                    }

                # --------------------------------------------------
                # Resume after approval.
                # --------------------------------------------------

                approval = (
                    await self.approval_service.get_request(
                        approval_request_id
                    )
                )

                if approval.status == ApprovalStatus.PENDING:

                    return {
                        "status": "APPROVAL_REQUIRED",
                        "plan_id": checkpoint.plan_id,
                        "operation_index": operation_index,
                        "approval_request": approval,
                        "results": checkpoint.results,
                    }

                if approval.status == ApprovalStatus.REJECTED:

                    checkpoint.rejected = True
                    checkpoint.rejection_reason = (
                        "Repository operation "
                        "was rejected by the user."
                    )

                    self._save_checkpoint(
                        workflow_state=workflow_state,
                        checkpoint=checkpoint,
                    )

                    return {
                        "status": "REJECTED",
                        "plan_id": checkpoint.plan_id,
                        "operation_index": operation_index,
                        "reason": checkpoint.rejection_reason,
                        "results": checkpoint.results,
                    }

                # Approved.
                checkpoint.pending_approval_request_id = None

                self._save_checkpoint(
                    workflow_state=workflow_state,
                    checkpoint=checkpoint,
                )

            # ======================================================
            # EXECUTE MCP TOOL
            # ======================================================

            result = self.mcp_tool_executor.execute(
                server_name=server_name,
                tool_name=planned_operation.tool_name,
                arguments=resolved_arguments,
            )

            if result is None:
                raise RuntimeError(
                    f"MCP tool '{planned_operation.tool_name}' "
                    "returned no result."
                )

            success = getattr(result, "success", True)

            if not success:

                error = getattr(result, "error", None)

                return {
                    "status": "FAILED",
                    "plan_id": checkpoint.plan_id,
                    "operation_index": operation_index,
                    "error": (
                        str(error)
                        if error
                        else (
                            f"MCP tool "
                            f"'{planned_operation.tool_name}' "
                            "failed."
                        )
                    ),
                    "results": checkpoint.results,
                }

            # ======================================================
            # STORE RESULT
            # ======================================================

            checkpoint.results.append(
                {
                    "operation_index": operation_index,
                    "operation": (
                        planned_operation.operation.value
                    ),
                    "tool_name": (
                        planned_operation.tool_name
                    ),
                    "arguments": resolved_arguments,
                    "result": result,
                }
            )

            # IMPORTANT:
            # Advance only AFTER successful execution.
            checkpoint.current_operation_index += 1

            self._save_checkpoint(
                workflow_state=workflow_state,
                checkpoint=checkpoint,
            )

        # ==========================================================
        # 5. COMPLETE
        # ==========================================================

        checkpoint.completed = True

        self._save_checkpoint(
            workflow_state=workflow_state,
            checkpoint=checkpoint,
        )

        return {
            "status": "COMPLETED",
            "plan_id": checkpoint.plan_id,
            "results": checkpoint.results,
        }

    # ==========================================================
    # CHECKPOINT
    # ==========================================================

    @staticmethod
    def _get_checkpoint(workflow_state):

        if workflow_state is None:
            return None

        app_state = getattr(
            workflow_state,
            "app_state",
            None,
        )

        if app_state is None:
            return None

        return getattr(
            app_state,
            "repository_execution_checkpoint",
            None,
        )

    @staticmethod
    def _save_checkpoint(
        workflow_state,
        checkpoint,
    ):

        if workflow_state is None:
            return

        app_state = getattr(
            workflow_state,
            "app_state",
            None,
        )

        if app_state is None:
            return

        app_state.repository_execution_checkpoint = (
            checkpoint
        )

    # ==========================================================
    # APPROVAL REQUEST
    # ==========================================================

    @staticmethod
    def _build_approval_request(
        plan,
        planned_operation,
        operation_index,
        arguments,
    ):

        request_id = (
            f"{plan.plan_id}:"
            f"{operation_index}"
        )

        return ApprovalRequest(
            request_id=request_id,
            action=planned_operation.operation.value,
            description=(
                f"Repository operation "
                f"'{planned_operation.operation.value}' "
                f"requires approval before executing "
                f"MCP tool "
                f"'{planned_operation.tool_name}'."
            ),
            details={
                "plan_id": plan.plan_id,
                "operation_index": operation_index,
                "tool_name": planned_operation.tool_name,
                "arguments": arguments,
            },
        )

    # ==========================================================
    # RESULT REFERENCES
    # ==========================================================

    def _resolve_result_references(
        self,
        value,
        results,
    ):

        if isinstance(value, dict):

            return {
                key: self._resolve_result_references(
                    item,
                    results,
                )
                for key, item in value.items()
            }

        if isinstance(value, list):

            return [
                self._resolve_result_references(
                    item,
                    results,
                )
                for item in value
            ]

        if not isinstance(value, str):
            return value

        if not value.startswith("$result."):
            return value

        reference = value[len("$result."):]

        parts = reference.split(".", 1)

        try:
            operation_index = int(parts[0])
        except ValueError:
            return value

        if (
            operation_index < 0
            or operation_index >= len(results)
        ):
            raise RuntimeError(
                f"Invalid repository result reference: "
                f"'{value}'."
            )

        result = results[operation_index]["result"]

        if len(parts) == 1:
            return result

        current = result

        for key in parts[1].split("."):

            if isinstance(current, dict):
                current = current.get(key)
            else:
                current = getattr(
                    current,
                    key,
                    None,
                )

        return current