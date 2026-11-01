from capabilities.base_capability import BaseCapability
from capabilities.code_push.code_push_capability import CodePushCapability
from capabilities.page_inspection.page_inspection_capability import (
    PageInspectionCapability,
)
from capabilities.repository.repository_capability import (
    RepositoryCapability,
)
from capabilities.repository_workspace.repository_workspace_capability import (
    RepositoryWorkspaceCapability,
)
from capabilities.test_execution.test_execution_capability import (
    TestExecutionCapability,
)
from registries.base_registry import BaseRegistry
from services.code_push_service import CodePushService
from services.workspace.automation_workspace_materializer import AutomationWorkspaceMaterializer
from capabilities.repository_analysis.repository_analysis_capability import (
    RepositoryAnalysisCapability,
)
from capabilities.test_gap_analysis.test_gap_analysis_capability import (
    TestGapAnalysisCapability,
)

class CapabilityRegistry(BaseRegistry[BaseCapability]):

    def __init__(
        self,
        execution_server_resolver,
        execution_provider_factory,
        mcp_execution_agent,
        mcp_tool_executor,
        repository_provider,
        repository_resolver,
        repository_discovery,
        automation_workspace_materializer: AutomationWorkspaceMaterializer,
        repository_analysis_agent,
        self_healing_service=None,
        approval_service=None,
        test_gap_analysis_service=None,
    ) -> None:

        super().__init__()

        self.execution_server_resolver = (
            execution_server_resolver
        )

        self.execution_provider_factory = (
            execution_provider_factory
        )

        self.mcp_execution_agent = (
            mcp_execution_agent
        )

        self.mcp_tool_executor = (
            mcp_tool_executor
        )

        self.repository_provider = (
            repository_provider
        )

        self.repository_resolver = (
            repository_resolver
        )

        self.repository_discovery = (
            repository_discovery
        )

        self.automation_workspace_materializer = (
            automation_workspace_materializer
        )

        self.repository_analysis_agent = (
            repository_analysis_agent
        )

        self.self_healing_service = self_healing_service
        self.approval_service = approval_service
        self.test_gap_analysis_service = test_gap_analysis_service

        self._register_default_capabilities()



    def get_executable_names(self) -> list[str]:

        """Return the names of all registered executable capabilities."""
        return self.get_registered_names()




    def _register_default_capabilities(
        self,
    ) -> None:

        # ==========================================================
        # Repository workspace acquisition
        # ==========================================================

        self.register(
            "repository_workspace",
            RepositoryWorkspaceCapability(
                repository_resolver=(
                    self.repository_resolver
                ),
            ),
        )


        self.register(
            "repository_analysis",
            RepositoryAnalysisCapability(
                repository_analysis_agent=self.repository_analysis_agent
            ),
        )




        # ==========================================================
        # Test execution
        # ==========================================================

        self.register(
            "test_execution",
            TestExecutionCapability(
                execution_server_resolver=self.execution_server_resolver,
                execution_provider_factory=self.execution_provider_factory,
                mcp_execution_agent=self.mcp_execution_agent,
                mcp_tool_executor=self.mcp_tool_executor,
                automation_workspace_materializer=self.automation_workspace_materializer,
                self_healing_service=self.self_healing_service,
            ),
        )

        # ==========================================================
        # Page inspection (Playwright MCP DOM snapshot)
        # ==========================================================

        self.register(
            "page_inspection",
            PageInspectionCapability(
                mcp_tool_executor=self.mcp_tool_executor,
            ),
        )

        # ==========================================================
        # Semantic repository operations
        # ==========================================================

        self.register(
            "repository",
            RepositoryCapability(
                repository_provider=(
                    self.repository_provider
                ),
            ),
        )

        # ==========================================================
        # Code push (branch + commit + push + PR)
        # ==========================================================

        if self.approval_service is not None:
            self.register(
                "code_push",
                CodePushCapability(
                    approval_service=self.approval_service,
                    code_push_service=CodePushService(),
                ),
            )

        # ==========================================================
        # Test gap analysis
        # ==========================================================

        if self.test_gap_analysis_service is not None:
            self.register(
                "test_gap_analysis",
                TestGapAnalysisCapability(
                    test_gap_analysis_service=self.test_gap_analysis_service,
                ),
            )



