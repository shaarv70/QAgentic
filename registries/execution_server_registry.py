from domain.execution.execution_server_config import ExecutionServerConfig
from registries.base_registry import BaseRegistry


class ExecutionServerRegistry(
    BaseRegistry[ExecutionServerConfig]
):

    def __init__(self):
        super().__init__()
        self._register_default_servers()

    def _register_default_servers(self) -> None:

        self.register(
            "selenium",
            ExecutionServerConfig(
                name="selenium",
                category="browser_automation",
                provider_type="mcp",
                server_name="selenium",
                tool_name=None,
                frameworks=("selenium",),

                enabled=True,
                priority=10,
            ),
        )

        self.register(
            "local-test-runner",
            ExecutionServerConfig(
                name="local-test-runner",
                category="test_runner",
                provider_type="local",
                server_name=None,
                tool_name=None,
                frameworks=(
                    "pytest",
                    "selenium",
                    "playwright",
                    "appium",
                    "restassured",
                ),
                enabled=True,
                priority=100,
            ),
        )

        # Future execution servers:
        #
        # self.register(
        #     "playwright",
        #     ExecutionServerConfig(...)
        # )
        #
        # self.register(
        #     "appium",
        #     ExecutionServerConfig(...)
        # )