import asyncio
import time
from typing import Any

from domain.execution.execution_policy import ExecutionPolicy
from capabilities.test_execution.models import TestExecutionResult
from capabilities.test_execution.ports.execution_provider import ExecutionProvider


class LocalExecutionProvider(ExecutionProvider):
    """
    Executes test commands on the local machine.

    The provider is framework-agnostic. The command determines
    which test runner is used, for example:

        pytest
        mvn
        gradle
        npm

    Security and execution limits are controlled by ExecutionPolicy.
    """

    def __init__(
        self,
        policy: ExecutionPolicy,
    ) -> None:

        self.policy = policy

    async def execute(
        self,
        command: str,
        working_directory: str,
        metadata: dict[str, Any] | None = None,
    ) -> TestExecutionResult:

        if not command or not command.strip():
            raise ValueError(
                "Execution command cannot be empty."
            )

        if not working_directory:
            raise ValueError(
                "Working directory cannot be empty."
            )

        if not self.policy.allow_shell:
            raise PermissionError(
                "Shell execution is disabled by the execution policy."
            )

        if not self.policy.is_command_allowed(command):
            executable = command.strip().split(
                maxsplit=1
            )[0]

            raise PermissionError(
                f"Execution of command '{executable}' "
                "is not allowed by the execution policy."
            )

        metadata = metadata or {}

        start_time = time.perf_counter()

        process = await asyncio.create_subprocess_shell(
            command,
            cwd=working_directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=None,
        )

        try:

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.policy.timeout_seconds,
            )

        except asyncio.TimeoutError:

            process.kill()

            await process.wait()

            duration = (
                time.perf_counter() - start_time
            )

            return TestExecutionResult(
                success=False,
                exit_code=-1,
                command=command,
                stdout="",
                stderr=(
                    "Execution timed out after "
                    f"{self.policy.timeout_seconds} seconds."
                ),
                duration_seconds=duration,
                metadata=metadata,
            )

        exit_code = process.returncode

        if exit_code is None:
            raise RuntimeError(
                "Process completed without an exit code."
            )

        duration = (
            time.perf_counter() - start_time
        )

        stdout_text = stdout[
            :self.policy.max_output_bytes
        ].decode(
            errors="replace"
        )

        stderr_text = stderr[
            :self.policy.max_output_bytes
        ].decode(
            errors="replace"
        )

        return TestExecutionResult(
            success=exit_code == 0,
            exit_code=exit_code,
            command=command,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_seconds=duration,
            metadata=metadata,
        )