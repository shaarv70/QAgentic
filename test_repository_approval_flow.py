import asyncio
from dataclasses import dataclass

from domain.repository.repository_execution_plan import (
    RepositoryExecutionOperation,
    RepositoryExecutionPlan,
)
from domain.repository.repository_operation import (
    RepositoryOperation,
    RepositoryOperationType,
)
from models.approval_model import ApprovalStatus
from services.approval.in_memory_approval_service import (
    InMemoryApprovalService,
)
from infrastructure.repository.mcp.mcp_repository_provider import (
    MCPRepositoryProvider,
)


@dataclass
class FakeMCPResult:
    """
    Minimal MCP result used by the test.

    We deliberately avoid a real MCP server here.

    This test validates repository orchestration:
        plan → checkpoint → approval → resume
    """

    success: bool = True
    data: dict | None = None
    error: str | None = None


class FakeMCPToolExecutor:
    """
    Fake MCP executor.

    Records every actual tool invocation so the test can verify
    that an operation waiting for approval was NOT executed.
    """

    def __init__(self):
        self.executed_tools = []
        self.discovery_count = 0

    async def discover_server_tools(
        self,
        server_name,
    ):
        self.discovery_count += 1

        return [
            {
                "name": "read_file",
                "description": "Read a repository file",
            },
            {
                "name": "modify_file",
                "description": "Modify a repository file",
            },
            {
                "name": "commit",
                "description": "Commit repository changes",
            },
        ]

    async def execute(
        self,
        server_name,
        tool_name,
        arguments,
    ):
        self.executed_tools.append(
            {
                "server_name": server_name,
                "tool_name": tool_name,
                "arguments": arguments,
            }
        )

        return FakeMCPResult(
            success=True,
            data={
                "tool": tool_name,
                "arguments": arguments,
            },
        )


class FakeRepositoryAgent:
    """
    Fake Repository Agent.

    The important assertion is that execute() must be called only
    once even though the workflow pauses/resumes multiple times.
    """

    def __init__(self):
        self.call_count = 0

    def execute(self, context):
        self.call_count += 1

        return RepositoryExecutionPlan(
            plan_id="test-plan-001",
            executable=True,
            reason=None,
            requires_approval=True,
            operations=[
                # Operation 0: READ
                RepositoryExecutionOperation(
                    operation=RepositoryOperationType.READ,
                    tool_name="read_file",
                    arguments={
                        "path": "src/example.py",
                    },
                ),

                # Operation 1: MODIFY
                RepositoryExecutionOperation(
                    operation=RepositoryOperationType.MODIFY,
                    tool_name="modify_file",
                    arguments={
                        "path": "src/example.py",
                        "content": "updated content",
                    },
                ),

                # Operation 2: MODIFY
                RepositoryExecutionOperation(
                    operation=RepositoryOperationType.MODIFY,
                    tool_name="modify_file",
                    arguments={
                        "path": "src/example2.py",
                        "content": "second update",
                    },
                ),

                # Operation 3: COMMIT
                RepositoryExecutionOperation(
                    operation=RepositoryOperationType.COMMIT,
                    tool_name="commit",
                    arguments={
                        "message": "Update files",
                    },
                ),
            ],
        )

class FakeApplicationState:
    """
    Minimal application state required by the repository
    execution test.

    Using an explicit class instead of dynamically creating a
    type() object keeps the test statically type-checkable.
    """

    def __init__(self) -> None:
        self.repository_execution_checkpoint = None

        
class FakeWorkflowState:
    """
    Minimal workflow state containing the application state
    required by MCPRepositoryProvider.
    """

    def __init__(self) -> None:
        self.app_state = FakeApplicationState()


def test_repository_approval_checkpoint_flow():
    """
    Verify:

        1. Plan is generated exactly once.
        2. READ executes immediately.
        3. MODIFY #1 requires approval.
        4. Approval resumes MODIFY #1.
        5. MODIFY #2 requires a separate approval.
        6. Approval resumes MODIFY #2.
        7. COMMIT requires another approval.
        8. Rejecting COMMIT stops execution.
    """

    async def run_test():

        mcp_executor = FakeMCPToolExecutor()
        repository_agent = FakeRepositoryAgent()
        approval_service = (
            InMemoryApprovalService()
        )

        provider = MCPRepositoryProvider(
            mcp_tool_executor=mcp_executor,
            repository_agent=repository_agent,
            approval_service=approval_service,
        )

        workflow_state = FakeWorkflowState()

        operation = RepositoryOperation(
            operation=RepositoryOperationType.MODIFY,
            arguments={},
        )

        repository = {
            "mcp_server": "test-repository-server",
        }

        # ======================================================
        # FIRST INVOCATION
        #
        # Expected:
        #
        #   READ executes
        #   MODIFY #1 pauses for approval
        # ======================================================

        result = await provider.execute(
            operation=operation,
            repository=repository,
            workflow_state=workflow_state,
        )

        assert result["status"] == "APPROVAL_REQUIRED"

        assert result["operation_index"] == 1

        # LLM must have been called exactly once.
        assert repository_agent.call_count == 1

        # READ should have executed.
        assert len(
            mcp_executor.executed_tools
        ) == 1

        assert (
            mcp_executor.executed_tools[0]["tool_name"]
            == "read_file"
        )

        checkpoint = (
            workflow_state
            .app_state
            .repository_execution_checkpoint
        )

        assert checkpoint is not None

        assert (
            checkpoint.current_operation_index
            == 1
        )

        assert (
            checkpoint.pending_approval_request_id
            == "test-plan-001:1"
        )

        # ======================================================
        # APPROVE MODIFY #1
        # ======================================================

        request_1 = (
            await approval_service.get_request(
                "test-plan-001:1"
            )
        )

        assert (
            request_1.status
            == ApprovalStatus.PENDING
        )

        await approval_service.approve(
            "test-plan-001:1"
        )

        # Resume execution.
        result = await provider.execute(
            operation=operation,
            repository=repository,
            workflow_state=workflow_state,
        )

        # ======================================================
        # MODIFY #2 SHOULD NOW BE THE NEXT APPROVAL.
        # ======================================================

        assert (
            result["status"]
            == "APPROVAL_REQUIRED"
        )

        assert (
            result["operation_index"]
            == 2
        )

        # The Repository Agent must NOT be called again.
        assert repository_agent.call_count == 1

        # READ + MODIFY #1 executed.
        assert len(
            mcp_executor.executed_tools
        ) == 2

        assert (
            mcp_executor.executed_tools[1][
                "tool_name"
            ]
            == "modify_file"
        )

        # ======================================================
        # APPROVE MODIFY #2
        # ======================================================

        await approval_service.approve(
            "test-plan-001:2"
        )

        result = await provider.execute(
            operation=operation,
            repository=repository,
            workflow_state=workflow_state,
        )

        # ======================================================
        # COMMIT SHOULD NOW REQUIRE APPROVAL.
        # ======================================================

        assert (
            result["status"]
            == "APPROVAL_REQUIRED"
        )

        assert (
            result["operation_index"]
            == 3
        )

        # Still exactly one plan generation.
        assert repository_agent.call_count == 1

        # READ + MODIFY #1 + MODIFY #2.
        assert len(
            mcp_executor.executed_tools
        ) == 3

        # COMMIT must NOT have executed yet.
        assert not any(
            item["tool_name"] == "commit"
            for item in mcp_executor.executed_tools
        )

        # ======================================================
        # REJECT COMMIT
        # ======================================================

        await approval_service.reject(
            "test-plan-001:3"
        )

        result = await provider.execute(
            operation=operation,
            repository=repository,
            workflow_state=workflow_state,
        )

        assert result["status"] == "REJECTED"

        # Commit must still never execute.
        assert not any(
            item["tool_name"] == "commit"
            for item in mcp_executor.executed_tools
        )

        # Plan still generated only once.
        assert repository_agent.call_count == 1

        checkpoint = (
            workflow_state
            .app_state
            .repository_execution_checkpoint
        )

        assert checkpoint is not None

        assert checkpoint.rejected is True

        assert (
            checkpoint.rejection_reason
            is not None
        )

    asyncio.run(run_test())