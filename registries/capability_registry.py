from capabilities.base_capability import BaseCapability
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
from services.workspace.automation_workspace_materializer import AutomationWorkspaceMaterializer
from capabilities.repository_analysis.repository_analysis_capability import (
    RepositoryAnalysisCapability,
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
                automation_workspace_materializer=self.automation_workspace_materializer
                ,
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



