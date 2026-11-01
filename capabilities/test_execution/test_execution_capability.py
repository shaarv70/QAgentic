import asyncio
import contextlib
import dataclasses
import io
import json
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

from capabilities.base_capability import BaseCapability
from models.capability_result import CapabilityResult
from models.automation_artifact import AutomationArtifact, AutomationFile
from capabilities.test_execution.models import TestExecutionRequest
from domain.execution.execution_errors import ExecutionPrerequisiteError
from models.execution_context import ExecutionContext

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
        self_healing_service=None,
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

        self.self_healing_service = self_healing_service

    @property
    def name(self) -> str:
        return "test_execution"

    @property
    def healable(self) -> bool:
        return self.self_healing_service is not None

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

            working_directory = self._resolve_workspace(
                request=request,
                context=context,
            )

            # --------------------------------------------------
            # 3a. Derive run command from automation artifact
            #     metadata when no profile/command was resolved.
            # --------------------------------------------------

            if not request.command:
                auto_command = self._extract_automation_run_command(
                    context=context,
                )
                if auto_command:
                    request.command = auto_command
                    logger.info(
                        "Resolved execution command from "
                        "automation artifact metadata | command=%r",
                        auto_command,
                    )

            # --------------------------------------------------
            # 3b. Validate
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
            # 5. Intelligent provider routing
            #
            # The capability decides whether to use MCP or local
            # execution by probing registered MCP servers at
            # runtime.  The planner no longer needs to emit a
            # correct execution_mode value — it is treated as an
            # advisory hint only.
            # --------------------------------------------------

            task_context = (
                task.context
                if isinstance(task, Task)
                else {}
            ) or {}

            provider_type, resolved_mcp_server = (
                self._resolve_provider_type(
                    request=request,
                    task_context=task_context,
                    category=category,
                )
            )

            # If routing chose MCP and discovered a server name,
            # bind it to the request so the resolver can find it.
            if (
                provider_type == "mcp"
                and resolved_mcp_server
                and not request.mcp_server
            ):
                request = dataclasses.replace(
                    request,
                    mcp_server=resolved_mcp_server,
                )

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

        except (PermissionError, ExecutionPrerequisiteError) as exc:
            # These errors are deterministic — retrying will always
            # produce the same result.  Fail immediately.
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
    # Intelligent provider routing
    # ==========================================================

    def _resolve_provider_type(
        self,
        request: TestExecutionRequest,
        task_context: dict,
        category: str | None,
    ) -> tuple[str, str | None]:
        """
        Decide whether to use MCP or local execution.

        Returns (provider_type, preferred_mcp_server_name).

        Decision order:
          1. Planner explicitly said "mcp"       → MCP
          2. Request already names an MCP server → MCP
          3. Probe registered MCP servers        → MCP if reachable
          4. Fall back to local execution        → local
        """

        raw_mode = (
            task_context.get("execution_mode") or ""
        ).strip().lower()

        # Planner explicitly requested MCP — trust it.
        if raw_mode == "mcp":
            logger.info(
                "execution_mode=mcp requested by planner "
                "— routing to MCP"
            )
            return "mcp", request.mcp_server

        # Request already names a specific MCP server.
        if request.mcp_server:
            logger.info(
                "Request names MCP server %r "
                "— routing to MCP",
                request.mcp_server,
            )
            return "mcp", request.mcp_server

        # Probe: can any registered MCP server handle this?
        mcp_server_name = self._probe_mcp_capability(
            framework=request.framework,
            category=category,
        )

        if mcp_server_name is not None:
            logger.info(
                "MCP server %r is available and supports "
                "framework=%r — routing to MCP",
                mcp_server_name,
                request.framework,
            )
            return "mcp", mcp_server_name

        if raw_mode and raw_mode not in {"local", "mcp"}:
            logger.debug(
                "Unrecognised execution_mode %r — treating as local",
                raw_mode,
            )

        logger.info(
            "No capable MCP server found "
            "— routing to local execution"
        )
        return "local", None

    def _probe_mcp_capability(
        self,
        framework: str | None,
        category: str | None,
    ) -> str | None:
        """
        Probe registered MCP servers to find one that can handle
        this execution request.

        Steps:
          1. Ask ExecutionServerResolver for an MCP server that
             matches the framework and category.
          2. Call discover_server_tools() to confirm it is
             reachable and has tools.

        Returns the server name if found, None otherwise.
        Never raises — all failures return None.
        """

        try:
            server = self.execution_server_resolver.resolve(
                framework=framework,
                category=category,
                provider_type="mcp",
            )
        except LookupError:
            logger.info(
                "No MCP server registered for "
                "framework=%r category=%r",
                framework,
                category,
            )
            return None

        server_name = server.server_name or server.name

        # Suppress noise emitted by anyio/httpcore async-generator
        # cleanup when the MCP connection is refused:
        #   • sys.unraisablehook — covers GC-raised exceptions
        #   • redirect_stderr   — covers asyncio call_exception_handler
        #     output ("an error occurred during closing of asynchronous
        #     generator") which bypasses sys.unraisablehook entirely.
        # Both hooks are restored unconditionally in the finally block.
        _original_unraisable_hook = sys.unraisablehook
        sys.unraisablehook = lambda _: None

        try:
            with contextlib.redirect_stderr(io.StringIO()):
                tools = asyncio.run(
                    self.mcp_tool_executor.discover_server_tools(
                        server_name
                    )
                )

            if tools:
                logger.info(
                    "MCP server %r responded with %d tool(s) "
                    "— MCP execution is available",
                    server_name,
                    len(tools),
                )
                return server_name

            logger.info(
                "MCP server %r is reachable but returned "
                "no tools — cannot handle request",
                server_name,
            )
            return None

        except (Exception, asyncio.CancelledError) as exc:
            # asyncio.CancelledError is BaseException (not Exception)
            # in Python 3.8+.  The MCP client raises it during cleanup
            # when a connection is refused, so it must be caught
            # explicitly here — otherwise it escapes to LangGraph which
            # treats CancelledError as a node cancellation signal.
            logger.info(
                "MCP server %r is not reachable (%s) "
                "— will use local execution",
                server_name,
                exc,
            )
            return None

        except BaseException as exc:
            # Python 3.11+ anyio task groups raise BaseExceptionGroup,
            # a subclass of BaseException not caught by except Exception.
            # Re-raise real signals; swallow connection-failure groups.
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            logger.info(
                "MCP server %r is not reachable (%s) "
                "— will use local execution",
                server_name,
                exc,
            )
            return None

        finally:
            sys.unraisablehook = _original_unraisable_hook

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

        logger.info(
            "Local execution finished | command=%r | exit_code=%s | "
            "stdout_chars=%d | stderr_chars=%d",
            command,
            result.exit_code,
            len(result.stdout or ""),
            len(result.stderr or ""),
        )

        if not result.success:
            # Maven/JVM runners write the meaningful failure to stdout
            # (BUILD FAILURE, test errors, stack traces).  stderr usually
            # contains only SLF4J/logging warnings that are not the real
            # failure reason.  Use the last 3000 chars of stdout to capture
            # the test summary; fall back to stderr if stdout is empty.
            stdout_tail = (result.stdout or "")[-3000:].strip()
            stderr_content = (result.stderr or "").strip()
            error_text = (
                stdout_tail
                or stderr_content
                or f"Command exited with code {result.exit_code}"
            )
            logger.warning(
                "Local execution failed | exit_code=%s | output=%.500s",
                result.exit_code,
                error_text,
            )
            return CapabilityResult(
                status="FAILED",
                data=result,
                error=error_text,
                retryable=False,
            )

        return CapabilityResult(
            status="PASSED",
            data=result,
            error=None,
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
                task_context.get("test_scope",
                    task_context.get("test_identifier"),
                ),
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

    def _extract_automation_run_command(
        self,
        context: Any,
    ) -> str | None:
        """
        Extract run_command from an AutomationArtifact's metadata block.

        Used when no repository_analysis profile was produced (pure
        generate-then-execute flows with no upstream repo cloning).
        """
        dependency_artifacts: Any = None

        if hasattr(context, "dependency_artifacts"):
            dependency_artifacts = context.dependency_artifacts
        elif isinstance(context, dict):
            dependency_artifacts = context.get("dependency_artifacts")

        if not dependency_artifacts:
            return None

        artifact = self._find_automation_artifact(dependency_artifacts)

        if artifact is None:
            return None

        run_command = (artifact.metadata or {}).get("run_command")

        return run_command if run_command else None

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
    # Self-healing correction
    # ==========================================================

    def correct(
        self,
        task: Any,
        context: Any,
        artifact: Any,
        feedback: Any,
    ) -> CapabilityResult:
        """
        Analyse the test failure and return a corrected execution result.

        Two healing paths are tried in order:

        1. Generated-artifact healing: an AutomationArtifact dependency exists
           (pure-generate flow).  The LLM patches the in-memory files and the
           workspace is re-materialised from scratch.

        2. Workspace healing: a WorkspaceArtifact dependency exists (repository-
           backed flow).  Failing source files are read from disk, patched by the
           LLM, written back to the workspace, and the tests are re-run.
        """

        if self.self_healing_service is None:
            raise NotImplementedError(
                "SelfHealingService is not wired up — "
                "cannot perform self-healing correction."
            )

        dependency_artifacts = getattr(
            context, "dependency_artifacts", {}
        ) or {}

        # --- Path 1: generated AutomationArtifact ---
        automation_artifact = self._find_automation_artifact(dependency_artifacts)
        if automation_artifact is not None:
            return self._heal_generated_artifact(
                task, context, artifact, dependency_artifacts, automation_artifact
            )

        # --- Path 2: repository workspace ---
        workflow_state = getattr(context, "workflow_state", None)
        workspace_artifact = self._find_workspace_for_healing(dependency_artifacts, workflow_state)
        if workspace_artifact is not None:
            return self._heal_workspace(task, context, artifact, workspace_artifact)

        logger.info(
            "Self-healing not applicable for repository test execution "
            "(no AutomationArtifact or WorkspaceArtifact found) — "
            "returning original failure"
        )
        return CapabilityResult(
            status="FAILED",
            data=getattr(artifact, "content", None),
            error="Self-healing not applicable: no patchable source found.",
            retryable=False,
        )

    def _heal_generated_artifact(
        self,
        task: Any,
        context: Any,
        artifact: Any,
        dependency_artifacts: dict,
        automation_artifact: AutomationArtifact,
    ) -> CapabilityResult:
        """Heal a pure-generate flow by patching the in-memory AutomationArtifact."""
        execution_output = self._extract_execution_output(artifact.content)
        requirement = getattr(context, "requirement", "") or ""

        logger.info(
            "Self-healing (generated): analysing failure | task=%s | output_chars=%d",
            task.task_id, len(execution_output),
        )

        healed_artifact = self.self_healing_service.heal(
            execution_output=execution_output,
            automation_artifact=automation_artifact,
            requirement=requirement,
            task=task,
        )

        logger.info(
            "Self-healing (generated): patch generated | task=%s | files=%d",
            task.task_id, len(healed_artifact.files),
        )

        healed_deps = self._replace_automation_artifact(dependency_artifacts, healed_artifact)
        healed_context = ExecutionContext(
            requirement=requirement,
            dependency_artifacts=healed_deps,
            workflow_state=getattr(context, "workflow_state", None),
        )

        result = self.execute(task, healed_context)

        if result.status == "PASSED":
            result.data = {
                "_healed_automation_artifact": healed_artifact,
                "_execution_result": result.data,
            }

        return result

    def _heal_workspace(
        self,
        task: Any,
        context: Any,
        artifact: Any,
        workspace_artifact: Any,
    ) -> CapabilityResult:
        """Heal a repository-backed flow by patching files in the cloned workspace."""
        execution_output = self._extract_execution_output(artifact.content)
        requirement = getattr(context, "requirement", "") or ""

        logger.info(
            "Self-healing (workspace): analysing failure | task=%s | workspace=%s",
            task.task_id, workspace_artifact.path,
        )

        workspace_files = self._extract_failing_workspace_files(
            execution_output, workspace_artifact.path
        )

        if not workspace_files:
            raise NotImplementedError(
                "Self-healing (workspace): could not identify source files "
                "to patch from the error output."
            )

        temp_artifact = AutomationArtifact(files=tuple(workspace_files))

        healed_artifact = self.self_healing_service.heal(
            execution_output=execution_output,
            automation_artifact=temp_artifact,
            requirement=requirement,
            task=task,
            workspace_path=workspace_artifact.path,
        )

        self._write_healed_files_to_workspace(healed_artifact, workspace_artifact.path)

        logger.info(
            "Self-healing (workspace): %d file(s) patched | task=%s",
            len(healed_artifact.files), task.task_id,
        )

        return self.execute(task, context)

    @staticmethod
    def _find_workspace_for_healing(dependency_artifacts: Any, workflow_state: Any = None) -> Any:
        """
        Locate a WorkspaceArtifact for self-healing.

        Checks direct dependency artifacts first, then falls back to scanning
        all artifacts in the workflow state.  The fallback is needed for
        repository-backed flows where test_execution only directly depends on
        repository_analysis, not repository_workspace — so the WorkspaceArtifact
        lives in a sibling artifact that is not a direct dependency.
        """
        if isinstance(dependency_artifacts, dict):
            for artifact in dependency_artifacts.values():
                if artifact is not None and hasattr(artifact, "path") and hasattr(artifact, "repository"):
                    return artifact

        # Scan all completed artifacts in the workflow state.
        # workflow_state may be a WorkflowState (has .app_state) or the
        # app_state itself (State, has .artifacts directly) — handle both.
        if workflow_state is not None:
            app_state = getattr(workflow_state, "app_state", None) or workflow_state
            for wrapped in getattr(app_state, "artifacts", {}).values():
                content = getattr(wrapped, "content", None)
                if content is not None and hasattr(content, "path") and hasattr(content, "repository"):
                    return content

        return None

    @staticmethod
    def _extract_failing_workspace_files(
        execution_output: str,
        workspace_path: str,
    ) -> list:
        """
        Parse Maven / javac / TestNG output to find source files that need
        healing, read them from disk, and return them as AutomationFile list.

        Two extraction passes are run in order:

        Pass 1 — absolute path references (compiler errors):
            /C:/path/MethodInterceptor.java:[14,43] cannot find symbol
            C:\\path\\File.java:[14,43]

        Pass 2 — stack trace class references (runtime failures such as
            Selenium NoSuchElementException, assertion errors, NPEs):
            at com.as.tests.LoginTest.testLogin(LoginTest.java:45)
            The class FQN is converted to a filesystem path and searched
            recursively under src/ inside the workspace.

        pom.xml is always appended so the LLM can also fix dependency issues.
        """
        import re
        from pathlib import Path

        workspace = Path(workspace_path).resolve()
        seen: set = set()
        files: list = []

        # ------------------------------------------------------------------
        # Pass 1 — absolute compiler-error paths
        # ------------------------------------------------------------------
        abs_pattern = re.compile(
            r"([A-Za-z]:[/\\][^\s:*?\"<>|]+\.(?:java|xml)"
            r"|/[A-Za-z]:/[^\s]+\.(?:java|xml)"
            r"|/[^\s:]+\.(?:java|xml)):\[?\d+",
            re.IGNORECASE,
        )

        for match in abs_pattern.finditer(execution_output):
            try:
                abs_path = Path(match.group(1)).resolve()
            except Exception:
                continue
            if abs_path in seen or not abs_path.exists():
                continue
            try:
                rel_path = abs_path.relative_to(workspace)
            except ValueError:
                continue
            seen.add(abs_path)
            files.append(AutomationFile(
                path=str(rel_path).replace("\\", "/"),
                content=abs_path.read_text(encoding="utf-8", errors="replace"),
            ))

        # ------------------------------------------------------------------
        # Pass 2 — stack trace class references (runtime failures)
        #
        # Matches lines like:
        #   at com.example.tests.LoginTest.someMethod(LoginTest.java:45)
        #   at com.example.PageObject.clickSubmit(PageObject.java:102)
        #
        # Strategy: extract the simple filename (LoginTest.java), then
        # search for it under src/ in the workspace.  This handles cases
        # where no absolute path is printed — e.g. Selenium locator failures,
        # assertion errors, NullPointerExceptions in test code.
        # ------------------------------------------------------------------
        stack_pattern = re.compile(
            r"\bat\s+[\w$.]+\.([\w$]+)\(([\w$]+\.java):(\d+)\)",
        )

        # Collect candidate simple filenames from the stack trace, skipping
        # known framework packages that are not in the workspace source tree.
        _FRAMEWORK_PREFIXES = (
            "org.testng.", "org.openqa.", "sun.", "java.", "javax.",
            "org.apache.", "com.google.", "io.github.", "net.bytebuddy.",
        )

        candidate_names: set = set()
        for match in stack_pattern.finditer(execution_output):
            fqn_prefix = match.group(0)  # full "at ..." line
            filename = match.group(2)    # e.g. "LoginTest.java"
            # Skip if the at-line starts with a known framework prefix
            at_class = re.search(r"at\s+([\w$.]+)\.", fqn_prefix)
            if at_class:
                cls = at_class.group(1)
                if any(cls.startswith(p) for p in _FRAMEWORK_PREFIXES):
                    continue
            candidate_names.add(filename)

        # Search workspace src/ tree for each candidate filename
        src_root = workspace / "src"
        if src_root.exists() and candidate_names:
            for java_file in src_root.rglob("*.java"):
                if java_file.name in candidate_names:
                    abs_path = java_file.resolve()
                    if abs_path in seen:
                        continue
                    seen.add(abs_path)
                    try:
                        rel_path = abs_path.relative_to(workspace)
                    except ValueError:
                        continue
                    files.append(AutomationFile(
                        path=str(rel_path).replace("\\", "/"),
                        content=abs_path.read_text(encoding="utf-8", errors="replace"),
                    ))

        # ------------------------------------------------------------------
        # Always include pom.xml — dependency / scope fixes are often needed
        # ------------------------------------------------------------------
        pom = workspace / "pom.xml"
        if pom.exists():
            pom_resolved = pom.resolve()
            if pom_resolved not in seen:
                files.append(AutomationFile(
                    path="pom.xml",
                    content=pom.read_text(encoding="utf-8", errors="replace"),
                ))

        return files

    @staticmethod
    def _write_healed_files_to_workspace(
        healed_artifact: AutomationArtifact,
        workspace_path: str,
    ) -> None:
        """Write healed files back into the repository workspace."""
        from pathlib import Path

        workspace = Path(workspace_path).resolve()
        for f in healed_artifact.files:
            target = (workspace / f.path).resolve()
            try:
                target.relative_to(workspace)
            except ValueError:
                logger.warning(
                    "Self-healing: skipping file that escapes workspace: %s", f.path
                )
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.content, encoding="utf-8")

    @staticmethod
    def _extract_execution_output(content: Any) -> str:
        """Extract human-readable failure output from an execution result."""
        if content is None:
            return "No execution output captured."

        # Local execution path: ExecutionResult object with .stdout/.stderr
        stdout = getattr(content, "stdout", None)
        stderr = getattr(content, "stderr", None)
        if stdout is not None or stderr is not None:
            parts = []
            if stdout:
                parts.append(f"STDOUT:\n{stdout}")
            if stderr:
                parts.append(f"STDERR:\n{stderr}")
            return "\n\n".join(parts) or "Execution produced no output."

        # MCP execution path: {"execution_plan": ..., "results": [...]}
        if isinstance(content, dict):
            texts = []
            for item in content.get("results", []):
                if not isinstance(item, dict):
                    continue
                res = item.get("result")
                if res is None:
                    continue
                for attr in ("stderr", "stdout", "error"):
                    val = getattr(res, attr, None) or (
                        item.get(attr) if isinstance(res, dict) else None
                    )
                    if val:
                        texts.append(f"{attr.upper()}:\n{val}")
            return "\n\n".join(texts) or "Execution produced no output."

        return str(content)[:3000]

    @staticmethod
    def _replace_automation_artifact(
        dependency_artifacts: dict,
        healed: AutomationArtifact,
    ) -> dict:
        """
        Return a copy of dependency_artifacts with every AutomationArtifact
        entry replaced by the healed version.
        """
        result = {}
        for dep_id, dep_content in dependency_artifacts.items():
            if isinstance(dep_content, AutomationArtifact):
                result[dep_id] = healed
            elif isinstance(dep_content, str):
                try:
                    AutomationArtifact.from_llm_content(dep_content)
                    result[dep_id] = healed
                except (ValueError, TypeError):
                    result[dep_id] = dep_content
            elif isinstance(dep_content, dict):
                try:
                    AutomationArtifact.from_dict(dep_content)
                    result[dep_id] = healed
                except (ValueError, TypeError):
                    result[dep_id] = dep_content
            else:
                result[dep_id] = dep_content
        return result

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

        # If the request names a specific test/suite and the profile has
        # not already selected one (LLM saw requested_suite=None), attempt
        # to match now so we pick the right command rather than AllTests.
        if request.test_path and not profile.selected_suite:
            profile.select_suite(request.test_path)
            if not profile.selected_suite:
                profile.set_selected_suite(request.test_path)

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

