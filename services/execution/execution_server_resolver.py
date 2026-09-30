from domain.execution.execution_server_config import (
ExecutionServerConfig,
)
from registries.base_registry import BaseRegistry

class ExecutionServerResolver:
    """
    Resolves the execution server that should handle a request.

    ```
    Resolution priority:

        1. Explicit server name
        2. Provider type
        3. Execution category
        4. Framework
        5. Server priority

    This resolver is intentionally independent of:
        - Selenium
        - Playwright
        - Appium
        - any specific MCP server
        - any specific test framework
    """

    def __init__(
        self,
        registry: BaseRegistry[ExecutionServerConfig],
    ) -> None:
        self._registry = registry

    def resolve(
        self,
        framework: str | None = None,
        category: str | None = None,
        server_name: str | None = None,
        provider_type: str | None = None,

    ) -> ExecutionServerConfig:
        """
        Resolve the most appropriate execution server.

        Explicit server_name always has highest priority.

        provider_type is useful when the caller explicitly requests
        a class of infrastructure, for example:

            provider_type="mcp"

        This does not identify any specific MCP vendor/server.
        """

        servers = [
            server
            for server in self._registry.values()
            if server.enabled
        ]

        if not servers:
            raise LookupError(
                "No enabled execution servers are registered."
            )

        # ----------------------------------------------------------
        # 1. Explicit server selection
        # ----------------------------------------------------------

        if server_name:
            for server in servers:
                if server.name == server_name:
                    return server

            raise LookupError(
                f"Execution server '{server_name}' was not found."
            )

        # ----------------------------------------------------------
        # 2. Provider type
        # ----------------------------------------------------------

        if provider_type:
            normalized_provider_type = (
                provider_type.strip().lower()
            )

            servers = [
                server
                for server in servers
                if server.provider_type.lower()
                == normalized_provider_type
            ]

        # ----------------------------------------------------------
        # 3. Execution category
        # ----------------------------------------------------------

        if category:
            normalized_category = (
                category.strip().lower()
            )

            category_matches = [
                server
                for server in servers
                if server.category.lower()
                == normalized_category
            ]

            if category_matches:
                servers = category_matches

        # ----------------------------------------------------------
        # 4. Framework
        # ----------------------------------------------------------

        if framework:
            normalized_framework = (
                framework.strip().lower()
            )

            framework_matches = [
                server
                for server in servers
                if normalized_framework
                in {
                    item.lower()
                    for item in server.frameworks
                }
            ]

            if framework_matches:
                servers = framework_matches

        # ----------------------------------------------------------
        # 5. Final resolution
        # ----------------------------------------------------------

        if not servers:
            raise LookupError(
                "No suitable execution server was found."
            )

        servers.sort(
            key=lambda server: server.priority
        )

        return servers[0]

