import asyncio
import glob
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from domain.execution.execution_errors import ExecutionPrerequisiteError
from domain.execution.execution_policy import ExecutionPolicy
from capabilities.test_execution.models import TestExecutionResult
from capabilities.test_execution.ports.execution_provider import ExecutionProvider
from utils.logger import logger


# ---------------------------------------------------------------------------
# Universal dependency pre-flight
# ---------------------------------------------------------------------------
#
# Each entry in _DEPENDENCY_CHECKS defines one ecosystem:
#   indicator   — file/dir that must exist to consider this ecosystem active
#   lock_or_dir — presence of this file/dir means deps are already installed
#                 (empty string → always install when indicator is present)
#   install_cmd — command to run when deps are missing
#
# Rules applied in order; all matching entries are prepended.
# Add new ecosystems here to support additional QA frameworks (Appium, etc.)
# without touching any other code.

_DEPENDENCY_CHECKS = [
    # Node.js / npm  ─ covers Playwright, Cypress, WebdriverIO, Appium JS
    {
        "indicator":   "package.json",
        "lock_or_dir": "node_modules",
        "install_cmd": "npm install",
    },
    # Ruby / Bundler  ─ covers Appium Ruby, Capybara
    {
        "indicator":   "Gemfile",
        "lock_or_dir": "vendor/bundle",
        "install_cmd": "bundle install",
    },
    # Go modules  ─ covers Appium Go client, custom runners
    {
        "indicator":   "go.mod",
        "lock_or_dir": "vendor",
        "install_cmd": "go mod download",
    },
    # .NET / NuGet  ─ covers Appium .NET, SpecFlow, NUnit
    {
        "indicator":   "*.csproj",       # glob — any .csproj in the root
        "lock_or_dir": "obj",
        "install_cmd": "dotnet restore",
    },
    # Python / pip  ─ covers Appium Python, Robot Framework, pytest + requests
    # Uses a .venv sentinel: only auto-install when a venv was set up but
    # site-packages looks empty, to avoid polluting the system Python.
    {
        "indicator":   "requirements.txt",
        "lock_or_dir": "",               # always install — pip is idempotent
        "install_cmd": "pip install -r requirements.txt",
    },
]


def _resolve_dependency_installs(command: str, working_directory: str) -> str:
    """
    Inspect the working directory, detect which dependency ecosystems are
    active, and prepend the relevant install commands when dependencies
    appear to be missing.

    Designed to be extended: add a new entry to _DEPENDENCY_CHECKS above
    to support any additional QA framework or runtime.
    """
    if not working_directory:
        return command

    wd = Path(working_directory)
    installs: list[str] = []

    for check in _DEPENDENCY_CHECKS:
        indicator = check["indicator"]
        lock_or_dir = check["lock_or_dir"]
        install_cmd = check["install_cmd"]

        # Skip if this ecosystem's install is already in the command.
        if install_cmd in command:
            continue

        # Check indicator (supports simple glob for patterns like *.csproj).
        if "*" in indicator:
            import glob as _glob
            indicator_present = bool(_glob.glob(str(wd / indicator)))
        else:
            indicator_present = (wd / indicator).exists()

        if not indicator_present:
            continue

        # If lock_or_dir is empty, always install (idempotent ecosystems).
        if not lock_or_dir:
            installs.append(install_cmd)
            continue

        # Install only when the lock/dir is absent (deps not yet resolved).
        if not (wd / lock_or_dir).exists():
            installs.append(install_cmd)

    if installs:
        prefix = " && ".join(installs)
        command = prefix + " && " + command
        logger.info(
            "Dependency pre-flight: prepended install(s) %r | full command=%r",
            installs,
            command,
        )

    return command


# ---------------------------------------------------------------------------
# JDK environment resolution
# ---------------------------------------------------------------------------

# Executables that require a full JDK (javac) rather than just a JRE.
_JDK_REQUIRED = frozenset({"mvn", "mvnw", "gradle", "gradlew"})

# Well-known system JDK installation roots (searched in addition to
# JAVA_HOME and PATH before surfacing an error to the user).
_WINDOWS_JDK_GLOBS = [
    "C:/Program Files/Eclipse Adoptium/jdk-*",
    "C:/Program Files/Eclipse Adoptium/jdk*",
    "C:/Program Files/Java/jdk*",
    "C:/Program Files/Microsoft/jdk-*",
    "C:/Program Files/BellSoft/LibericaJDK-*",
    "C:/Program Files/Azul Systems/Zulu*",
    "C:/Program Files/Amazon Corretto/*",
    # User-writable locations (corporate laptops without admin rights)
    os.path.expanduser("~/jdk-*"),
    os.path.expanduser("~/jdk*"),
    os.path.expanduser("~/.jdk/jdk-*"),
    os.path.expanduser("~/.jdk/jdk*"),
    os.path.expanduser("~/AppData/Local/jdk-*"),
    os.path.expanduser("~/AppData/Local/jdk*"),
]
_UNIX_JDK_GLOBS = [
    "/usr/lib/jvm/java-*-openjdk*",
    "/usr/lib/jvm/jdk*",
    "/Library/Java/JavaVirtualMachines/*/Contents/Home",
]


def _javac_bin() -> str:
    return "javac.exe" if os.name == "nt" else "javac"


def _find_system_jdk() -> str | None:
    """Return the newest JDK found in well-known system directories, or None."""
    patterns = _WINDOWS_JDK_GLOBS if os.name == "nt" else _UNIX_JDK_GLOBS
    candidates = [
        d
        for pattern in patterns
        for d in glob.glob(pattern)
        if (Path(d) / "bin" / _javac_bin()).is_file()
    ]
    return sorted(candidates, reverse=True)[0] if candidates else None


def _build_env_for_command(command: str) -> dict:
    """
    Build a subprocess environment for the given command.

    For JVM build tools (mvn, gradle, gradlew, mvnw) this ensures
    JAVA_HOME points to a JDK that contains javac.  The resolution
    order is:

      1. Current JAVA_HOME already contains javac  → use as-is
      2. javac found on PATH                        → use current env
      3. JDK found in well-known install locations  → patch JAVA_HOME + PATH

    If no JDK can be located, an ExecutionPrerequisiteError is raised
    with a clear message telling the user what to install.
    """
    executable = Path(command.strip().split(maxsplit=1)[0]).stem.lower()
    env = os.environ.copy()

    if executable not in _JDK_REQUIRED:
        return env

    sep = ";" if os.name == "nt" else ":"

    def _patch(jdk_home: str) -> dict:
        env["JAVA_HOME"] = jdk_home
        env["PATH"] = str(Path(jdk_home) / "bin") + sep + env.get("PATH", "")
        return env

    # 1. Current JAVA_HOME already points to a JDK?
    java_home = env.get("JAVA_HOME", "")
    if java_home and (Path(java_home) / "bin" / _javac_bin()).is_file():
        logger.debug("JDK confirmed via JAVA_HOME | path=%s", java_home)
        return env

    # 2. javac already reachable via PATH?
    if shutil.which("javac"):
        logger.debug("javac found on PATH — JDK available")
        return env

    # 3. Search well-known system installation directories.
    jdk_home = _find_system_jdk()
    if jdk_home:
        logger.info("JDK found on system — patching JAVA_HOME | path=%s", jdk_home)
        return _patch(jdk_home)

    # No JDK found anywhere — tell the user exactly what to do.
    raise ExecutionPrerequisiteError(
        "A JDK (Java Development Kit) is required to compile and run Java tests, "
        "but only a JRE (Java Runtime Environment) was found on this machine.\n"
        "Please install JDK 11 or later:\n"
        "  • Windows / macOS / Linux: https://adoptium.net\n"
        "After installation, set the JAVA_HOME environment variable to the JDK "
        "directory and ensure javac is on your PATH."
    )


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

        # Resolve the subprocess environment (patches JAVA_HOME etc. when needed).
        env = _build_env_for_command(command)

        # Universal dependency pre-flight: detect missing dependencies for any
        # QA ecosystem (npm, bundler, go, dotnet, pip) and prepend their
        # install commands so the test command never fails due to missing deps.
        import re as _re
        command = _resolve_dependency_installs(command, working_directory or "")

        # Normalise Playwright commands for automated (non-interactive) execution.
        #
        # Two things keep the subprocess alive after the test finishes and
        # prevent process.wait() from ever returning:
        #
        #   1. --headed  → browser window stays open until manually closed.
        #   2. HTML report plugins (e.g. ortoni-report) start an HTTP server
        #      on a fixed port and wait for Ctrl+C.  CI=1 suppresses the
        #      terminal prompt but does NOT stop the server itself.
        #
        # Fix: strip --headed and inject --reporter=line so the HTML reporter
        # is replaced by a plain line reporter that writes to stdout and exits.
        if "playwright" in command.lower():
            if "--headed" in command:
                command = _re.sub(r"\s*--headed\b", "", command).strip()
            if "--reporter" not in command:
                command = command + " --reporter=line"
            logger.info(
                "Normalised Playwright command for automated execution | command=%r",
                command,
            )

        start_time = time.perf_counter()

        # Use temp files instead of PIPE for stdout/stderr.
        #
        # On Windows, browser-based test runners (Selenium, Playwright) spawn
        # child processes (Chrome, ChromeDriver) that inherit the pipe handles
        # from the Maven/pytest parent.  asyncio.communicate() waits for pipe
        # EOF, which never arrives while those grandchildren are alive — causing
        # Python to hang indefinitely even after the test command itself exits.
        #
        # Writing to temp files and calling process.wait() (which only waits
        # for the direct child) avoids that inheritance problem entirely.
        stdout_fd, stdout_path = tempfile.mkstemp(prefix="qagentic_stdout_")
        stderr_fd, stderr_path = tempfile.mkstemp(prefix="qagentic_stderr_")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_directory,
                stdout=stdout_fd,
                stderr=stderr_fd,
                env=env,
            )

            # Close our copies of the FDs — the child process owns them now.
            os.close(stdout_fd)
            os.close(stderr_fd)
            stdout_fd = stderr_fd = -1

            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=self.policy.timeout_seconds,
                )

            except asyncio.TimeoutError:
                # Kill the entire process tree so we don't leave orphan
                # browser / driver processes consuming resources.
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/T", "/F", "/PID", str(process.pid)],
                        capture_output=True,
                    )
                process.kill()
                await process.wait()

                duration = time.perf_counter() - start_time

                return TestExecutionResult(
                    success=False,
                    exit_code=-1,
                    command=command,
                    stdout="",
                    stderr=(
                        f"Execution timed out after {self.policy.timeout_seconds} seconds."
                    ),
                    duration_seconds=duration,
                    metadata=metadata,
                )

            exit_code = process.returncode

            if exit_code is None:
                raise RuntimeError("Process completed without an exit code.")

            duration = time.perf_counter() - start_time

            with open(stdout_path, "rb") as f:
                stdout_text = f.read()[:self.policy.max_output_bytes].decode(errors="replace")

            with open(stderr_path, "rb") as f:
                stderr_text = f.read()[:self.policy.max_output_bytes].decode(errors="replace")

        finally:
            for fd in (stdout_fd, stderr_fd):
                if fd >= 0:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            for path in (stdout_path, stderr_path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

        return TestExecutionResult(
            success=exit_code == 0,
            exit_code=exit_code,
            command=command,
            stdout=stdout_text,
            stderr=stderr_text,
            duration_seconds=duration,
            metadata=metadata,
        )