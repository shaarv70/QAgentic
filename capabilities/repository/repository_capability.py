import asyncio
import os
import subprocess

from capabilities.base_capability import BaseCapability
from utils.logger import logger
from domain.repository.repository_operation import (
    RepositoryOperation,
    RepositoryOperationType,
)
from models.capability_result import CapabilityResult


# ---------------------------------------------------------------------------
# Helpers for local-path → remote-URL resolution
# ---------------------------------------------------------------------------

def _is_local_path(value: str) -> bool:
    """Return True when value looks like a local filesystem path."""
    if not value:
        return False
    # Windows absolute path (C:\...) or UNC path
    if len(value) >= 2 and value[1] == ":":
        return True
    # Unix absolute path
    if value.startswith("/"):
        return True
    # Relative path markers
    if value.startswith(".") or "\\" in value:
        return True
    return os.path.isabs(value)


def _git_remote_url(path: str) -> str:
    """
    Run `git remote get-url origin` inside path and return the remote URL.
    Returns an empty string on any error.
    """
    if not path or not os.path.isdir(path):
        return ""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            remote = result.stdout.strip()
            logger.info(
                "Discovered git remote URL | path=%s | remote=%s", path, remote
            )
            return remote
    except Exception as exc:
        logger.debug("git remote get-url failed | path=%s | %s", path, exc)
    return ""


def _current_branch(path: str) -> str:
    """Return the active git branch name, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _default_branch(path: str) -> str:
    """Return the default remote branch (e.g. 'main'), or 'main' as fallback."""
    try:
        result = subprocess.run(
            ["git", "remote", "show", "origin"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in result.stdout.splitlines():
            if "HEAD branch" in line:
                return line.split(":")[-1].strip()
    except Exception:
        pass
    return "main"


def _branch_to_title(branch: str) -> str:
    """Convert 'feature/v0.6-e2e-pipeline' into a readable PR title."""
    import re
    name = re.sub(
        r"^(feature|fix|bugfix|hotfix|chore|refactor|docs|test|feat)[/\-]",
        "",
        branch,
        flags=re.IGNORECASE,
    )
    name = re.sub(r"[-_/]+", " ", name).strip()
    return name.capitalize() or branch


def _enrich_from_local_git(local_path: str, repository: dict, operation: str) -> dict:
    """
    Enrich repository dict with owner, name, head, base, and title
    discovered from the local git repository.  Only fills in fields
    that are currently empty / null.  Called when the planner supplies
    a local path rather than a hosted repository URL.
    """
    enriched = dict(repository)

    remote_url = _git_remote_url(local_path)
    if remote_url:
        import re
        m = re.search(r"[:/]([^/]+)/([^/]+?)(?:\.git)?$", remote_url)
        if m:
            if not enriched.get("owner"):
                enriched["owner"] = m.group(1)
            if not enriched.get("name"):
                enriched["name"] = m.group(2)

    if "create_pull_request" in operation or "pull_request" in operation:
        head = _current_branch(local_path)
        base = _default_branch(local_path)
        if head and not enriched.get("head"):
            enriched["head"] = head
        if base and not enriched.get("base"):
            enriched["base"] = base
        if head and not enriched.get("title"):
            enriched["title"] = _branch_to_title(head)
        logger.info(
            "Enriched repository context from local git | owner=%s | head=%s | base=%s | title=%r",
            enriched.get("owner"),
            enriched.get("head"),
            enriched.get("base"),
            enriched.get("title"),
        )

    return enriched


class RepositoryCapability(BaseCapability):

    def __init__(self, repository_provider):
        self.repository_provider = repository_provider

    @property
    def name(self) -> str:
        return "repository"

    def correct(
        self,
        task,
        context=None,
        artifact=None,
        feedback=None,
    ) -> CapabilityResult:
        # Clear the checkpoint so MCPRepositoryProvider starts a fresh
        # re-plan instead of replaying the same completed checkpoint.
        self._clear_checkpoint(context)
        return self.execute(task, context)

    @staticmethod
    def _clear_checkpoint(context) -> None:
        workflow_state = (
            getattr(context, "workflow_state", None)
            if context is not None
            else None
        )
        if workflow_state is None:
            return
        app_state = getattr(workflow_state, "app_state", None)
        if app_state is not None:
            app_state.repository_execution_checkpoint = None

    def execute(
        self,
        task,
        context=None,
    ) -> CapabilityResult:

        try:
            operation = self._build_operation(task)

            repository = self._build_repository_context(
                task=task,
                context=context,
            )

            workflow_state = (
                getattr(
                    context,
                    "workflow_state",
                    None,
                )
                if context is not None
                else None
            )

            result = asyncio.run(
                self.repository_provider.execute(
                    operation=operation,
                    repository=repository,
                    workflow_state=workflow_state,
                )
            )

            if (
                isinstance(result, dict)
                and result.get("status")
                == "APPROVAL_REQUIRED"
            ):
                return CapabilityResult(
                    status="PENDING_APPROVAL",
                    data=result,
                    error=result.get("reason"),
                    retryable=False,
                )

            if (
                isinstance(result, dict)
                and result.get("status")
                == "REJECTED"
            ):
                return CapabilityResult(
                    status="FAILED",
                    data=result,
                    error=(
                        result.get("reason")
                        or "Repository operation was rejected."
                    ),
                    retryable=False,
                )

            return CapabilityResult(
                status="PASSED",
                data=result,
                error=None,
            )

        except (TypeError, ValueError) as exc:

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
                retryable=True,
            )

    def _build_operation(self, task) -> RepositoryOperation:

        context = task.context or {}

        operation_value = context.get("operation")

        if operation_value is None:
            raise ValueError(
                "Repository task is missing 'operation'."
            )

        try:
            operation_type = RepositoryOperationType(
                operation_value
            )
        except ValueError as exc:
            raise ValueError(
                f"Unsupported repository operation: "
                f"{operation_value}"
            ) from exc

        arguments = context.get(
            "arguments",
            {},
        )

        if not isinstance(arguments, dict):
            raise TypeError(
                "Repository operation arguments "
                "must be a dictionary."
            )

        return RepositoryOperation(
            operation=operation_type,
            arguments=arguments,
        )

    def _build_repository_context(
        self,
        task,
        context=None,
    ) -> dict:

        task_context = task.context or {}

        repository = task_context.get("repository")

        if repository is None:
            # Planner may emit flat keys instead of a nested dict.
            repository = self._assemble_repository_context(task_context)

        if not isinstance(repository, dict):
            raise TypeError(
                "Repository context must be a dictionary."
            )

        if not repository.get("mcp_server"):
            repository = dict(repository)
            repository["mcp_server"] = self._infer_mcp_server(
                repository, task_context
            )

        # When the planner supplies a local path, enrich the repository dict
        # with owner, name, head branch, base branch, and PR title so the
        # RepositoryExecution agent doesn't have to invent or refuse them.
        local_path = (
            repository.get("local_path")
            or task_context.get("repo_path")
            or task_context.get("repository_path")
        )
        raw_url = repository.get("url") or ""
        if not local_path and _is_local_path(raw_url):
            local_path = raw_url
        if local_path and os.path.isdir(str(local_path)):
            operation = (task_context.get("operation") or "").lower()
            repository = _enrich_from_local_git(str(local_path), repository, operation)

        return repository

    @staticmethod
    def _assemble_repository_context(task_context: dict) -> dict:
        url = (
            task_context.get("repository_url")
            or task_context.get("url")
            or ""
        )
        owner = task_context.get("repository_owner") or task_context.get("owner") or ""
        name = task_context.get("repository_name") or task_context.get("name") or ""

        if url and (not owner or not name):
            # Parse owner/name from https://host/owner/name[.git]
            import re
            m = re.search(r"[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
            if m:
                owner = owner or m.group(1)
                name = name or m.group(2)

        if not url and not owner and not name:
            raise ValueError(
                "Repository task is missing 'repository' context. "
                "Provide a 'repository' dict or at least "
                "'repository_url'/'repository_owner'/'repository_name'."
            )

        return {
            "url": url,
            "owner": owner,
            "name": name,
        }

    @staticmethod
    def _infer_mcp_server(repository: dict, task_context: dict) -> str:
        raw_url = (
            repository.get("url")
            or task_context.get("repository_url")
            or ""
        )
        platform = (task_context.get("platform") or "").lower()

        url = raw_url.lower()

        _KNOWN_PLATFORMS = ("github", "gitlab", "bitbucket", "azure", "devops")

        # If the URL doesn't already identify a platform, attempt to discover
        # the remote URL from the local git repository.  The planner may emit:
        #   - a full local path as url  (e.g. "C:\Users\...\QAgentic")
        #   - url="local" with the real path in repository["local_path"]
        #   - repo_path / repository_path in task context
        if not any(p in url for p in _KNOWN_PLATFORMS):
            local_path_candidates = [
                repository.get("local_path"),
                task_context.get("repo_path"),
                task_context.get("repository_path"),
                raw_url if _is_local_path(raw_url) else None,
            ]
            for candidate in local_path_candidates:
                if not candidate:
                    continue
                discovered = _git_remote_url(candidate)
                if discovered:
                    url = discovered.lower()
                    break

        if "github" in url or "github" in platform:
            return "github"
        if "gitlab" in url or "gitlab" in platform:
            return "gitlab"
        if "bitbucket" in url or "bitbucket" in platform:
            return "bitbucket"
        if "azure" in url or "devops" in url or "azure" in platform:
            return "azure_devops"

        raise ValueError(
            "Cannot determine MCP server from repository context. "
            "Set 'mcp_server' explicitly in the task context."
        )