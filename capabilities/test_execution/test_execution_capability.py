import asyncio
import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from capabilities.base_capability import BaseCapability
from models.capability_result import CapabilityResult
from models.automation_artifact import AutomationArtifact
from capabilities.test_execution.models import TestExecutionRequest

from models.repository_execution_profile import RepositoryExecutionProfile
from services.execution.execution_provider_factory import (
    ExecutionProviderFactory,
)

from models.task import Task

from services.execution.execution_server_resolver import (
    ExecutionServerResolver,
)

from services.workspace.automation_workspace_materializer import AutomationWorkspaceMaterializer
from utils.logger import logger


class TestExecutionCapability(BaseCapability):
    """
    Coordinates automated test and execution workflows.

    This capability is intentionally provider-agnostic.

    It does not contain logic specific to:
        - Selenium
        - Playwright
        - Appium
        - REST clients
        - any specific MCP server
        - any specific test framework

    Responsibilities:

        1. Normalize the execution task.
        2. Resolve the execution workspace supplied by the
           repository/workspace layer.
        3. Validate the execution request.
        4. Resolve the execution server.
        5. Create the execution provider.
        6. Delegate MCP planning to MCPExecutionAgent.
        7. Delegate MCP tool execution to MCPToolExecutor.
        8. Return a CapabilityResult.

    Repository cloning, checkout, workspace allocation, and
    repository discovery are outside this capability.
    """

    def __init__(
        self,
        execution_server_resolver: ExecutionServerResolver,
        execution_provider_factory: ExecutionProviderFactory,
        mcp_execution_agent,
        mcp_tool_executor,
        automation_workspace_materializer: AutomationWorkspaceMaterializer,
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

        self.automation_workspace_materializer = (
            automation_workspace_materializer
        )

    @property
    def name(self) -> str:
        return "test_execution"

    # ==========================================================
    # Public execution entry point
    # ==========================================================

    def execute(
        self,
        task: Any,
        context: Any = None,
    ) -> Any:
        """
        Execute a test/execution task.

        Supported inputs:

            Task
                Normal QAgentic execution path.

            TestExecutionRequest
                Direct capability invocation.

        Execution flow:

            Task
              ↓
            TestExecutionRequest
              ↓
            Execution workspace supplied by repository layer
              ↓
            Validation
              ↓
            ExecutionServerResolver
              ↓
            ExecutionProviderFactory
              ↓
            Local execution OR MCP execution
        """

        try:

            # --------------------------------------------------
            # 1. Normalize task
            # --------------------------------------------------

            request = self._build_request(task)


            # --------------------------------------------------
            # 2. Resolve repository execution profile
            # --------------------------------------------------

            repository_execution_profile = (
                self._find_repository_execution_profile(
                    context=context,
                )
            )

            request = self._apply_execution_profile(
                request=request,
                profile=repository_execution_profile,
            )

    # --------------------------------------------------
    # 3. Resolve execution workspace
    # --------------------------------------------------
            # --------------------------------------------------
            # 2. Resolve execution workspace
            # --------------------------------------------------

            working_directory = self._resolve_workspace(
                request=request,
                context=context,
            )

            # --------------------------------------------------
            # 3. Validate
            # --------------------------------------------------

            self._validate_request(
                request=request,
            )

            # --------------------------------------------------
            # 4. Resolve execution category
            # --------------------------------------------------

            category = (
                self._resolve_execution_category(
                    request=request,
                    task=task,
                )
            )

            # --------------------------------------------------
            # 5. Resolve provider type
            # --------------------------------------------------

            task_context = (
                task.context
                if isinstance(task, Task)
                else {}
            )

            execution_mode = (
                task_context.get("execution_mode")
                if isinstance(task_context, dict)
                else None
            )

            if execution_mode:
                normalized_mode = execution_mode.strip().lower()

                if normalized_mode not in {"local", "mcp"}:
                    raise ValueError(
                        f"Unsupported execution mode: {execution_mode}"
                    )

                provider_type = normalized_mode

            elif request.command and not request.mcp_server:
                # A concrete executable command without an explicit MCP
                # server is a local execution request.
                provider_type = "local"

            else:
                provider_type = None

            # --------------------------------------------------
            # 6. Resolve execution server
            # --------------------------------------------------

            server = (
                self.execution_server_resolver.resolve(
                    framework=request.framework,
                    category=category,
                    server_name=request.mcp_server,
                    provider_type=provider_type,
                )
            )

            # --------------------------------------------------
            # 7. Create provider
            # --------------------------------------------------

            provider = (
                self.execution_provider_factory.create(
                    server
                )
            )

            # --------------------------------------------------
            # 8. Execute
            # --------------------------------------------------

            if server.provider_type == "local":

                return self._execute_local(
                    request=request,
                    working_directory=working_directory,
                    provider=provider,
                )

            if server.provider_type == "mcp":

                return self._execute_mcp(
                    request=request,
                    task=task,
                    working_directory=working_directory,
                    server=server,
                )

            raise RuntimeError(
                "Unsupported execution provider type: "
                f"{server.provider_type}"
            )

        except Exception as exc:

            return CapabilityResult(
                status="FAILED",
                data=None,
                error=str(exc),
            )

    # ==========================================================
    # Execution category
    # ==========================================================

    def _resolve_execution_category(
        self,
        request: TestExecutionRequest,
        task: Any,
    ) -> str | None:
        """
        Resolve the generic execution category.

        Category is execution metadata.

        The capability deliberately does NOT derive category
        from a specific tool name or vendor/framework.

        Examples:

            test_runner
            browser_automation
            mobile_automation
            api_automation
            remote_execution
        """

        task_context = {}

        if isinstance(task, Task):
            task_context = task.context or {}

        execution_category = task_context.get(
            "execution_category"
        )

        if execution_category:
            return execution_category

        execution_mode = task_context.get(
            "execution_mode"
        )

        if execution_mode == "mcp":
            return None

        if request.command:
            return "test_runner"

        return None

    # ==========================================================
    # Local execution
    # ==========================================================

    def _execute_local(
        self,
        request: TestExecutionRequest,
        working_directory: str,
        provider,
    ) -> CapabilityResult:

        command = request.command

        if not command:
            raise ValueError(
                "Repository analysis did not provide an "
                "executable test command."
            )

        result = asyncio.run(
            provider.execute(
                command=command,
                working_directory=working_directory,
                metadata={
                    "framework": request.framework,
                    "repository_path": request.repository_path,
                    "repository_url": request.repository_url,
                    "branch": request.branch,
                    "test_path": request.test_path,
                },
            )
        )

        return CapabilityResult(
            status=(
                "PASSED"
                if result.success
                else "FAILED"
            ),
            data=result,
            error=(
                None
                if result.success
                else result.stderr
            ),
        )

    # ==========================================================
    # MCP execution
    # ==========================================================

    def _execute_mcp(
        self,
        request: TestExecutionRequest,
        task: Any,
        working_directory: str,
        server,
    ) -> CapabilityResult:

        # --------------------------------------------------
        # 1. Discover available tools
        # --------------------------------------------------

        available_tools = asyncio.run(
            self.mcp_tool_executor.discover_server_tools(
                server.server_name or server.name
            )
        )

        if not available_tools:
            raise RuntimeError(
                "No MCP tools were discovered on "
                f"execution server '{server.name}'."
            )

        # --------------------------------------------------
        # 2. Build semantic execution context
        # --------------------------------------------------

        execution_context = (
            self._build_execution_context(
                request=request,
                task=task,
                working_directory=working_directory,
                server=server,
            )
        )

        # --------------------------------------------------
        # 3. Ask MCPExecutionAgent for a plan
        # --------------------------------------------------

        plan = self.mcp_execution_agent.execute(
            {
                "execution_context": execution_context,
                "available_tools": available_tools,
            }
        )

        if plan is None:
            raise RuntimeError(
                "MCPExecutionAgent returned no "
                "execution plan."
            )

        # --------------------------------------------------
        # 4. Handle unsupported execution
        # --------------------------------------------------

        if not plan.executable:

            logger.warning(
                "MCP execution is not supported: "
                f"{plan.reason}"
            )

            return CapabilityResult(
                status="FAILED",
                data=None,
                error=plan.reason,
            )

        if not plan.operations:
            raise RuntimeError(
                "MCP execution plan is marked executable "
                "but contains no operations."
            )

        # --------------------------------------------------
        # 5. Execute planned MCP operations
        # --------------------------------------------------

        results = []
        execution_results = {}

        mcp_server_name = (
            server.server_name
            or server.name
        )

        for operation in plan.operations:

            # ----------------------------------------------
            # Resolve references from previous operations
            # ----------------------------------------------

            resolved_arguments = (
                self._resolve_result_references(
                    arguments=operation.arguments,
                    execution_results=execution_results,
                )
            )

            # ----------------------------------------------
            # Execute MCP tool
            # ----------------------------------------------

            result = asyncio.run(
                self.mcp_tool_executor.execute(
                    server_name=mcp_server_name,
                    tool_name=operation.tool_name,
                    arguments=resolved_arguments,
                )
            )

            # ----------------------------------------------
            # Store result for dependent operations
            # ----------------------------------------------

            execution_results[
                operation.tool_name
            ] = result

            results.append(
                {
                    "tool_name": operation.tool_name,
                    "arguments": resolved_arguments,
                    "result": result,
                }
            )

            # ----------------------------------------------
            # Stop execution after failed operation
            # ----------------------------------------------

            if hasattr(result, "success"):

                if not result.success:

                    return CapabilityResult(
                        status="FAILED",
                        data={
                            "execution_plan": plan,
                            "results": results,
                        },
                        error=(
                            getattr(
                                result,
                                "error",
                                None,
                            )
                            or getattr(
                                result,
                                "stderr",
                                None,
                            )
                            or "MCP operation failed."
                        ),
                    )

        return CapabilityResult(
            status="PASSED",
            data={
                "execution_plan": plan,
                "results": results,
            },
            error=None,
        )

    # ==========================================================
    # Build semantic execution context
    # ==========================================================

    def _build_execution_context(
        self,
        request: TestExecutionRequest,
        task: Any,
        working_directory: str,
        server,
    ) -> dict[str, Any]:

        task_context = {}

        if isinstance(task, Task):
            task_context = (
                task.context or {}
            )

        return {
            "task": {
                "task_id": getattr(
                    task,
                    "task_id",
                    None,
                ),
                "description": getattr(
                    task,
                    "description",
                    None,
                ),
            },

            "execution": {
                "category": task_context.get(
                    "execution_category"
                ),
                "mode": task_context.get(
                    "execution_mode"
                ),
                "framework": request.framework,
                "command": request.command,
                "test_path": request.test_path,
            },

            "repository": {
                "path": request.repository_path,
                "url": request.repository_url,
                "branch": request.branch,
                "working_directory": working_directory,
            },

            "execution_server": {
                "name": server.name,
                "provider_type": server.provider_type,
                "server_name": server.server_name,
            },

            "requested_tool": request.tool_name,

            "tool_arguments": (
                request.tool_arguments or {}
            ),

            "task_context": task_context,
        }

    # ==========================================================
    # Request normalization
    # ==========================================================

    def _build_request(
        self,
        task: Any,
    ) -> TestExecutionRequest:

        if isinstance(
            task,
            TestExecutionRequest,
        ):
            return task

        if not isinstance(
            task,
            Task,
        ):
            raise TypeError(
                "TestExecutionCapability expects "
                "a Task or TestExecutionRequest."
            )

        task_context = (
            task.context or {}
        )

        return TestExecutionRequest(
            repository_path=task_context.get(
                "repository_path",
                task_context.get("repo_path"),
            ),
            repository_url=task_context.get(
                "repository_url",
                task_context.get("repo_url"),
            ),
            branch=task_context.get("branch"),
            framework=task_context.get("framework"),
            mcp_server=task_context.get("mcp_server"),
            command=task_context.get("command"),
            tool_name=task_context.get("tool_name"),
            tool_arguments=task_context.get(
                "tool_arguments"
            ),
            test_path=task_context.get(
                "test_path",
                task_context.get("test_scope"),
            ),
        )

    # ==========================================================
    # Workspace resolution
    # ==========================================================

    def _resolve_workspace(
        self,
        request: TestExecutionRequest,
        context: Any,
    ) -> str:
        """
        Resolve an execution workspace.

        There are two supported paths:

        1. An already prepared workspace supplied by an upstream
           repository/workspace capability.
        2. Generated automation source supplied by an upstream
           automation task. In that case this capability materializes
           an isolated Maven workspace for execution.

        Repository cloning/checkout remains outside this capability.
        """

        # --------------------------------------------------
        # 1. Existing workspace artifact from an upstream task
        # --------------------------------------------------
        if hasattr(context, "dependency_artifacts"):
            dependency_artifacts = context.dependency_artifacts

            workspace = self._find_workspace_artifact(
                dependency_artifacts
            )

            if workspace is not None:
                return self._validate_workspace_path(
                    workspace.path
                )

            generated_workspace = self._materialize_generated_workspace(
                dependency_artifacts=dependency_artifacts,
                task_context=self._get_task_context(context),
            )

            if generated_workspace is not None:
                return generated_workspace

        # --------------------------------------------------
        # 2. Direct context dictionary
        # --------------------------------------------------
        if isinstance(context, dict):
            workspace = context.get("workspace")

            if workspace is not None:
                if hasattr(workspace, "path"):
                    return self._validate_workspace_path(
                        workspace.path
                    )

                if isinstance(workspace, str):
                    return self._validate_workspace_path(
                        workspace
                    )

                raise TypeError(
                    "Execution workspace must be a "
                    "WorkspaceArtifact or string path."
                )

            generated_workspace = self._materialize_generated_workspace(
                dependency_artifacts=context.get(
                    "dependency_artifacts",
                    {},
                ),
                task_context=context,
            )

            if generated_workspace is not None:
                return generated_workspace

        # --------------------------------------------------
        # 3. Direct workspace path
        # --------------------------------------------------
        if isinstance(context, str):
            return self._validate_workspace_path(context)

        # --------------------------------------------------
        # 4. Existing repository path compatibility
        # --------------------------------------------------
        if request.repository_path:
            return self._validate_workspace_path(
                request.repository_path
            )

        raise ValueError(
            "Test execution requires an execution workspace."
        )

    @staticmethod
    def _find_workspace_artifact(
        dependency_artifacts: Any,
    ) -> Any:
        """
        Find an upstream workspace artifact without coupling execution
        to a specific capability name.
        """
        if not isinstance(dependency_artifacts, dict):
            return None

        for artifact in dependency_artifacts.values():
            if artifact is None:
                continue

            path = getattr(artifact, "path", None)

            if path:
                return artifact

        return None

    @staticmethod
    def _get_task_context(context: Any) -> dict[str, Any]:
        workflow_state = getattr(context, "workflow_state", None)

        if workflow_state is not None:
            app_state = getattr(workflow_state, "app_state", None)

            if app_state is not None:
                # The task context is not guaranteed to be present in
                # application state, so return an empty dictionary.
                return {}

        return {}

    def _materialize_generated_workspace(
        self,
        dependency_artifacts: Any,
        task_context: dict[str, Any],
    ) -> str | None:
        """
        Materialize a structured AutomationArtifact into an isolated
        execution workspace.

        Automation generation produces the structured artifact.
        Execution owns materialization into a real workspace.
        """

        artifact = self._find_automation_artifact(
            dependency_artifacts
        )

        if artifact is None:
            return None

        root = (
            Path(".qagentic")
            / "workspaces"
            / "generated"
            / str(uuid.uuid4())
        ).resolve()

        workspace_artifact = (
            self.automation_workspace_materializer.materialize(
                artifact=artifact,
                workspace_path=root,
            )
        )

        workspace_path = self._validate_workspace_path(
            workspace_artifact.path
        )

        logger.info(
            "Generated automation materialized | "
            f"workspace={workspace_path}"
        )

        return workspace_path

    @staticmethod
    def _find_automation_artifact(
        dependency_artifacts: Any,
    ) -> AutomationArtifact | None:
        """
        Locate a structured AutomationArtifact in dependency artifacts.

        Native AutomationArtifact objects are preferred. Serialized JSON
        and dictionary representations are also supported because
        workflow/checkpoint boundaries may serialize artifacts.
        """

        if not isinstance(dependency_artifacts, dict):
            return None

        for artifact in dependency_artifacts.values():
            if isinstance(
                artifact,
                AutomationArtifact,
            ):
                return artifact

            if isinstance(
                artifact,
                str,
            ):
                try:
                    return AutomationArtifact.from_llm_content(
                        artifact
                    )
                except (
                    ValueError,
                    TypeError,
                    json.JSONDecodeError,
                ):
                    continue

            if isinstance(
                artifact,
                dict,
            ):
                try:
                    return AutomationArtifact.from_dict(
                        artifact
                    )
                except (
                    ValueError,
                    TypeError,
                ):
                    continue

        return None

    def _validate_workspace_path(
    self,
    workspace_path: str,
) -> str:
        """
        Validate an already-prepared execution workspace.
        """

        if not workspace_path:
            raise ValueError(
                "Execution workspace path cannot be empty."
            )

        path = (
            Path(workspace_path)
            .expanduser()
            .resolve()
        )

        if not path.exists():
            raise FileNotFoundError(
                "Execution workspace does not exist: "
                f"{path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                "Execution workspace is not a directory: "
                f"{path}"
            )

        return str(path)

    # ==========================================================
    # Validation
    # ==========================================================

    def _validate_request(
        self,
        request: TestExecutionRequest,
    ) -> None:

        if (
            not request.repository_path
            and not request.repository_url
            and not request.command
            and not request.tool_name
        ):
            raise ValueError(
                "Test execution does not contain enough "
                "information to determine what should be executed."
            )

        # Framework is required for local test-runner execution
        # when it cannot be discovered elsewhere.
        #
        # MCP execution does not require a framework.

        # A generated automation workspace has a concrete Maven test
        # command even when the planner did not provide a framework field.
        # The provider is still selected by execution_mode/category.

    # ==========================================================
    # Correction
    # ==========================================================

    def correct(
        self,
        task: Any,
        context: Any,
        artifact: Any,
        feedback: Any,
    ) -> Any:

        raise NotImplementedError(
            "Correction for test execution is "
            "not implemented yet."
        )

    # ==========================================================
    # Result reference resolution
    # ==========================================================

    def _resolve_result_references(
        self,
        arguments: Any,
        execution_results: dict[str, Any],
    ) -> Any:

        if isinstance(
            arguments,
            dict,
        ):

            return {
                key: self._resolve_result_references(
                    value,
                    execution_results,
                )
                for key, value in arguments.items()
            }

        if isinstance(
            arguments,
            list,
        ):

            return [
                self._resolve_result_references(
                    value,
                    execution_results,
                )
                for value in arguments
            ]

        if not isinstance(
            arguments,
            str,
        ):
            return arguments

        if not arguments.startswith(
            "$result."
        ):
            return arguments

        path = (
            arguments[
                len("$result.") :
            ].split(".")
        )

        if len(path) < 2:
            raise RuntimeError(
                f"Invalid result reference "
                f"'{arguments}'. Expected "
                "'$result.<tool_name>.<field>'."
            )

        tool_name = path[0]
        field_path = path[1:]

        if (
            tool_name
            not in execution_results
        ):
            raise RuntimeError(
                f"Result reference '{arguments}' "
                "cannot be resolved. "
                f"No result exists for tool "
                f"'{tool_name}'."
            )

        value = execution_results[
            tool_name
        ]

        # Support CapabilityResult-like wrappers.

        if hasattr(
            value,
            "data",
        ):
            value = value.data

        for field in field_path:

            if isinstance(
                value,
                dict,
            ):

                if field not in value:
                    raise RuntimeError(
                        f"Result reference "
                        f"'{arguments}' cannot be "
                        f"resolved. Field '{field}' "
                        "was not found."
                    )

                value = value[field]

            elif hasattr(
                value,
                field,
            ):

                value = getattr(
                    value,
                    field,
                )

            else:

                raise RuntimeError(
                    f"Result reference "
                    f"'{arguments}' cannot be "
                    f"resolved. Field '{field}' "
                    "is not available."
                )

        return value


        # ==========================================================
    # Repository execution profile
    # ==========================================================

    @staticmethod
    def _find_repository_execution_profile(
    context: Any,
) -> RepositoryExecutionProfile | None:
        """
        Find the RepositoryExecutionProfile produced by the
        repository_analysis capability.

        The execution capability consumes the profile but does not
        perform repository analysis itself.
        """

        dependency_artifacts = None

        if hasattr(context, "dependency_artifacts"):
            dependency_artifacts = context.dependency_artifacts

        elif isinstance(context, dict):
            dependency_artifacts = context.get(
                "dependency_artifacts"
            )

        if not isinstance(dependency_artifacts, dict):
            return None

        for artifact in dependency_artifacts.values():

            if isinstance(
                artifact,
                RepositoryExecutionProfile,
            ):
                return artifact

        return None



    @staticmethod
    def _apply_execution_profile(
        request: TestExecutionRequest,
        profile: RepositoryExecutionProfile | None,
    ) -> TestExecutionRequest:

        if profile is None:
            return request

        command = request.command

        if not command:
            selected_command = profile.selected_command

            if selected_command is not None:
                command = selected_command.command

        framework = (
            request.framework
            or profile.selected_framework
        )

        test_path = request.test_path

        if not test_path and profile.test_locations:
            test_path = profile.test_locations[0]

        return TestExecutionRequest(
            repository_path=(
                request.repository_path
                or profile.working_directory
            ),
            repository_url=request.repository_url,
            branch=request.branch,
            framework=framework,
            mcp_server=request.mcp_server,
            command=command,
            tool_name=request.tool_name,
            tool_arguments=request.tool_arguments,
            test_path=test_path,
        )

