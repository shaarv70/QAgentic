from collections.abc import Iterable
import re
from typing import Any

from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from constants.agent_names import AgentNames
from models.action_spec import ActionSpec
from models.plan import Plan
from models.task import Task


class PlanningService:
    """
    Build and validate an executable plan from action contracts.

    PlanningService is intentionally domain-agnostic. It does not contain
    knowledge about OrangeHRM, Selenium, repositories, login flows, or any
    particular user prompt.
    """

    def __init__(
        self,
        ai_service,
        available_actions: Iterable[ActionSpec],
        prompt_builder: PromptBuilder,
    ):
        self.ai_service = ai_service
        self.available_actions = list(available_actions)

        self._action_names = {
            action.name
            for action in self.available_actions
        }

        self._action_specs = {
            action.name: action
            for action in self.available_actions
        }

        self.prompt_builder = prompt_builder

    def create_plan(self, requirement, intelligence):

        prompt = self.prompt_builder.planner(requirement,
        intelligence,
    [
        action.to_dict()
        for action in self.available_actions
    ],
)

        request = LLMRequest(
    system_prompt=prompt.system_prompt,
    user_prompt=prompt.user_prompt,
)

        response = self.ai_service.generate_json(
            AgentNames.PLANNER,
            request,
        )

        tasks_data = self._extract_tasks(response)

        if not isinstance(tasks_data, list) or not tasks_data:
            raise ValueError(
                "Planner response must contain a non-empty 'tasks' list."
            )

        plan = Plan()

        intelligence_context = self._get_intelligence_context(
            intelligence
        )
        skipped_task_ids: set[str] = set()
        # Maps LLM-assigned index IDs (task_1, task_2, …) to the
        # renumbered IDs that actually appear in the plan.  When a task
        # is skipped the counter does not advance, so downstream tasks
        # get consecutive IDs (task_1, task_2) instead of (task_2, task_3).
        old_id_to_new_id: dict[str, str] = {}
        task_counter = 0

        for index, raw_task_data in enumerate(tasks_data, start=1):
            if not isinstance(raw_task_data, dict):
                raise ValueError(
                    f"Planner task at index {index} must be an object."
                )

            raw_task_data = self._normalize_raw_task(raw_task_data)

            # If capability is still absent but "name" matches a known action
            # (e.g. model emitted {"name":"testcase","description":"..."}),
            # promote name to capability.
            if (
                not raw_task_data.get("capability")
                and raw_task_data.get("name") in self._action_names
            ):
                raw_task_data = dict(raw_task_data)
                raw_task_data["capability"] = raw_task_data["name"]

            task_data = self._normalize_task_contract(
                raw_task_data,
                intelligence_context,
            )

            task_data = self._ensure_repository_workspace_context(
                task_data=task_data,
                requirement=requirement,
                intelligence_context=intelligence_context,
            )

            if task_data is None:
                skipped_task_ids.add(f"task_{index}")
                continue

            task_counter += 1
            new_task_id = f"task_{task_counter}"
            # Map by enumerate-index key (task_1, task_2, …)
            old_id_to_new_id[f"task_{index}"] = new_task_id
            # Also map by whatever task_id the model actually used
            # (e.g. "task_001", "task_a", "step_1") so dependency
            # references are resolved regardless of model ID format.
            model_task_id = task_data.get("task_id") or ""
            if model_task_id and model_task_id != f"task_{index}":
                old_id_to_new_id[model_task_id] = new_task_id

            action_name = (
                task_data.get("capability")
                or task_data.get("action")
            )

            if action_name not in self._action_names:
                from utils.logger import logger as _log
                import json as _json
                _log.info(
                    "Planner task with bad capability | action=%r | task=%s",
                    action_name,
                    _json.dumps(task_data, default=str)[:500],
                )
                raise ValueError(
                    "Planner returned unsupported executable action: "
                    f"{action_name!r} (known: {sorted(self._action_names)})"
                )

            description = task_data.get("description")

            if (
                not isinstance(description, str)
                or not description.strip()
            ):
                raise ValueError(
                    f"Planner task {index} is missing a description."
                )

            planner_context = task_data.get("context", {})

            if planner_context is None:
                planner_context = {}

            if not isinstance(planner_context, dict):
                raise ValueError(
                    f"Planner context for task_{index} "
                    "must be an object."
                )

            task_context = self._build_task_context(
                requirement=requirement,
                intelligence_context=intelligence_context,
                planner_context=planner_context,
            )

            task = Task(
                task_id=new_task_id,
                capability=action_name,
                description=description.strip(),
                context=task_context,
                depends_on=[],
            )

            raw_dependencies = task_data.get("depends_on", [])

            if not isinstance(raw_dependencies, list):
                raw_dependencies = [raw_dependencies]

            # Translate LLM task IDs to renumbered IDs, dropping any
            # dependency on a skipped task.
            translated_dependencies: list = []
            for dep in raw_dependencies:
                old_dep_id = self._dependency_task_id(dep)
                if old_dep_id in skipped_task_ids:
                    continue
                mapped = old_id_to_new_id.get(old_dep_id)
                translated_dependencies.append(
                    mapped if mapped is not None else dep
                )

            task.depends_on = self._normalize_dependencies(
                task_id=task.task_id,
                raw_dependencies=translated_dependencies,
                planned_tasks=plan.tasks,
            )

            plan.tasks.append(task)

        self._enforce_implicit_dependencies(plan)
        self._inject_analysis_for_local_workspace(
            plan=plan,
            requirement=requirement,
            intelligence_context=intelligence_context,
        )
        self._validate_plan(plan)

        plan.priority = response.get(
            "priority",
            "MEDIUM",
        )

        plan.parallel = response.get(
            "parallel",
            True,
        )

        return plan



    @staticmethod
    def _extract_tasks(response: dict) -> list:
        """
        Extract the tasks list from a planner response that may use
        any of the observed structural variants:
          {"tasks": [...]}
          {"plan": [...]}
          {"plan": {"tasks": [...], ...}}
          {"plan": {"goal": "...", "tasks": [...]}}
        """
        if not isinstance(response, dict):
            return []

        tasks = response.get("tasks")
        if isinstance(tasks, list):
            return tasks

        for key in ("plan", "workflow"):
            value = response.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                tasks = value.get("tasks")
                if isinstance(tasks, list):
                    return tasks

        return []

    @staticmethod
    def _enforce_implicit_dependencies(plan: Plan) -> None:
        """
        Enforce known implicit dependencies that the planner model sometimes omits.

        Rule 1: test_execution MUST depend on automation when both are in the plan.
        Rule 2: test_execution MUST depend on repository_analysis when both are in the plan.
        """
        automation_ids = {
            task.task_id
            for task in plan.tasks
            if task.capability == "automation"
        }
        repo_analysis_ids = {
            task.task_id
            for task in plan.tasks
            if task.capability == "repository_analysis"
        }
        if not automation_ids and not repo_analysis_ids:
            return
        for task in plan.tasks:
            if task.capability != "test_execution":
                continue
            existing_deps = set(task.depends_on or [])
            if automation_ids and not existing_deps.intersection(automation_ids):
                existing_deps |= automation_ids
            if repo_analysis_ids and not existing_deps.intersection(repo_analysis_ids):
                existing_deps |= repo_analysis_ids
            task.depends_on = sorted(existing_deps)

    def _inject_analysis_for_local_workspace(
        self,
        plan: Plan,
        requirement,
        intelligence_context: dict,
    ) -> None:
        """
        Safety net: when test_execution is planned without repository_analysis
        but a local directory path is detectable, inject repository_analysis as
        task_1 and make test_execution depend on it.

        For local paths no repository_workspace task is needed — repository_analysis
        resolves the workspace path from task context and test_execution uses
        profile.working_directory via _apply_execution_profile.
        """
        from utils.logger import logger as _log

        if "repository_analysis" not in self._action_names:
            return

        has_test_execution = any(
            t.capability == "test_execution" for t in plan.tasks
        )
        has_repo_analysis = any(
            t.capability == "repository_analysis" for t in plan.tasks
        )

        if not has_test_execution or has_repo_analysis:
            return

        import re as _re
        from pathlib import Path as _Path

        _WIN_PATH_RE = _re.compile(r"[A-Za-z]:[/\\]")
        # Handles both single-backslash (C:\dir) and double-backslash
        # (C:\\dir, from JSON serialization) Windows paths.
        _WIN_PATH_EXTRACT = _re.compile(
            r"[A-Za-z]:[/\\]{1,2}(?:[^\s\\/:*?\"<>|]+[/\\]{1,2})*[^\s\\/:*?\"<>|]+"
        )

        def _is_abs_path(s: str) -> bool:
            # Exclude URLs — "s://" in "https://" matches [A-Za-z]:[/\\]
            # but is not a local filesystem path.
            if "://" in s:
                return False
            if (len(s) > 2 and s[1] == ":" and s[2] in "/\\") or s.startswith("/"):
                return True
            return bool(_WIN_PATH_RE.search(s))

        def _extract_local_dir(s: str) -> str | None:
            # Normalize double backslashes before matching so JSON-serialized
            # paths (C:\\Users\\...) are treated the same as C:\Users\...
            normalized = s.replace("\\\\", "\\")
            for match in _WIN_PATH_EXTRACT.finditer(normalized):
                candidate = match.group(0).rstrip(".,;)")
                p = _Path(candidate)
                if p.is_dir():
                    return str(p)
                if p.parent.is_dir():
                    return str(p.parent)
            return None

        requirement_str = (
            requirement if isinstance(requirement, str) else str(requirement or "")
        )
        context_values = (
            list(intelligence_context.values())
            if isinstance(intelligence_context, dict)
            else []
        )
        all_strings = [requirement_str] + [
            v for v in context_values if isinstance(v, str)
        ]

        if not any(_is_abs_path(s) for s in all_strings):
            return

        # Extract the normalized local directory path to inject explicitly as
        # workspace_path so _resolve_workspace_path finds it without regex fallback.
        local_path: str | None = None
        for s in all_strings:
            local_path = _extract_local_dir(s)
            if local_path:
                break

        # No valid local directory found — do not inject a repository_analysis
        # task with an empty workspace_path (happens when the requirement contains
        # a URL like https://... that passes the path regex but is not a real path).
        if local_path is None:
            return

        # Renumber existing tasks: task_N → task_(N+1).
        old_to_new: dict[str, str] = {}
        for task in plan.tasks:
            tid = task.task_id
            if tid.startswith("task_") and tid[5:].isdigit():
                old_to_new[tid] = f"task_{int(tid[5:]) + 1}"

        for task in plan.tasks:
            new_id = old_to_new.get(task.task_id)
            if new_id:
                task.task_id = new_id
            task.depends_on = [
                old_to_new.get(d, d) for d in (task.depends_on or [])
            ]

        for task in plan.tasks:
            if (
                task.capability == "test_execution"
                and "task_1" not in task.depends_on
            ):
                task.depends_on = ["task_1"] + task.depends_on

        injected_context = self._build_task_context(
            requirement=requirement,
            intelligence_context=intelligence_context,
            planner_context={},
        )

        # Inject the resolved path explicitly — bypasses the regex fallback in
        # _resolve_workspace_path which breaks on double-backslash strings.
        if local_path:
            injected_context["workspace_path"] = local_path

        plan.tasks.insert(0, Task(
            task_id="task_1",
            capability="repository_analysis",
            description=(
                "Analyze local workspace to determine the test framework, "
                "runner, suite selector, and execution strategy."
            ),
            context=injected_context,
            depends_on=[],
        ))

        _log.info(
            "Injected repository_analysis as task_1 for local workspace | "
            "test_execution tasks renumbered"
        )

    @staticmethod
    def _normalize_raw_task(raw: dict) -> dict:
        """
        Normalise field names the model sometimes varies.

        Handled aliases:
          "id"        → "task_id"    (when task_id absent)
          "name"      → "description" (when description absent)
          "type" / "step_type" / "tool" / "action_type" / "kind"
                      → "capability"  (when capability absent/null, OR when
                                       capability is itself set to a meta-label
                                       alias name rather than an actual
                                       capability value — e.g. capability="tool")
        Returns a new dict; never mutates the original.
        """
        # Field names that the model sometimes uses AS the value of capability
        # instead of as sibling keys.  These are meta-labels, not valid
        # capability names, and must be resolved via sibling fields.
        # "capability" itself is included so that kind="capability" is treated
        # as a meta-label rather than a real capability name.
        _ALIAS_NAMES = frozenset(
            ("type", "step_type", "tool", "action_type", "kind", "capability")
        )

        out = dict(raw)

        if not out.get("task_id") and out.get("id"):
            out["task_id"] = out["id"]

        if not out.get("description") and out.get("name"):
            out["description"] = out["name"]

        capability_raw = out.get("capability")

        # Resolve capability from alias sibling fields when:
        #   (a) capability is absent/null, OR
        #   (b) capability is itself a meta-label name (e.g. "tool", "kind",
        #       or literally "capability") rather than a real capability value.
        if not capability_raw or capability_raw in _ALIAS_NAMES:
            if capability_raw in _ALIAS_NAMES:
                # Clear the meta-label so we replace it with the real value.
                out["capability"] = None
            # "action" is checked first — it is the most common field the LLM
            # uses to carry the real capability name alongside a "kind" field.
            for alias in ("action", "type", "step_type", "tool", "action_type", "kind"):
                candidate = out.get(alias)
                if candidate and candidate not in _ALIAS_NAMES:
                    out["capability"] = candidate
                    break

        # Last-resort fallback: use capability as description when the model
        # omits both "description" and "name" (e.g. repository_analysis tasks).
        if not out.get("description") and out.get("capability"):
            out["description"] = out["capability"]

        return out

    def _normalize_dependencies(
        self,
        task_id: str,
        raw_dependencies: Any,
        planned_tasks: list[Task],
    ) -> list[str]:

        if raw_dependencies is None:
            return []

        if not isinstance(raw_dependencies, list):
            raw_dependencies = [raw_dependencies]

        known_by_name = {
            task.capability: task.task_id
            for task in planned_tasks
        }

        normalized: list[str] = []

        known_task_ids = {
            task.task_id
            for task in planned_tasks
        }

        for dependency in raw_dependencies:

            reference = self._extract_dependency_reference(
                dependency
            )

            if reference is None:
                raise ValueError(
                    f"Planner dependency for '{task_id}' "
                    f"is invalid: {dependency!r}"
                )

            dependency_id = self._normalize_dependency_reference(
                reference=reference,
                task_id=task_id,
                known_by_name=known_by_name,
            )

            if dependency_id == task_id:
                raise ValueError(
                    f"Task '{task_id}' cannot depend on itself."
                )

            if dependency_id not in known_task_ids:
                raise ValueError(
                    f"Planner dependency '{dependency_id}' "
                    f"for '{task_id}' does not reference "
                    "an earlier task."
                )

            if dependency_id not in normalized:
                normalized.append(dependency_id)

        return normalized



    @staticmethod
    def _dependency_task_id(value: Any) -> str | None:
        """Return a canonical task id without raising validation errors."""
        reference = PlanningService._extract_dependency_reference(value)
        if reference is None:
            return None
        if isinstance(reference, int):
            return f"task_{reference}"
        normalized = reference.strip()
        if not normalized:
            return None
        if normalized.isdigit():
            return f"task_{int(normalized)}"
        if normalized.startswith("task_") and normalized[5:].isdigit():
            # Strip leading zeros: "task_001" → "task_1"
            return f"task_{int(normalized[5:])}"
        if normalized.startswith("task") and normalized[4:].isdigit():
            return f"task_{int(normalized[4:])}"
        # Handle LLM-generated shorthand IDs: T1, T2, T3 → task_1, task_2, task_3
        if len(normalized) >= 2 and normalized[0].upper() == "T" and normalized[1:].isdigit():
            return f"task_{int(normalized[1:])}"
        return normalized

    @staticmethod
    def _extract_dependency_reference(
        value: Any,
    ) -> str | int | None:

        if isinstance(value, int):
            return value

        if isinstance(value, str):
            return value

        if isinstance(value, dict):

            for key in (
                "task_id",
                "task",
                "action",
                "capability",
                "name",
            ):
                candidate = value.get(key)

                if isinstance(candidate, (str, int)):
                    return candidate

        return None



    @staticmethod
    def _normalize_dependency_reference(
        reference: str | int,
        task_id: str,
        known_by_name: dict[str, str],
    ) -> str:

        if isinstance(reference, int):

            if reference <= 0:
                raise ValueError(
                    f"Planner dependency for '{task_id}' "
                    "must reference a positive task number."
                )

            return f"task_{reference}"

        value = reference.strip()

        if not value:
            raise ValueError(
                f"Planner dependency for '{task_id}' "
                "cannot be empty."
            )

        if value.isdigit():

            number = int(value)

            if number <= 0:
                raise ValueError(
                    f"Planner dependency for '{task_id}' "
                    "must reference a positive task number."
                )

            return f"task_{number}"

        if value.startswith("task_") and value[5:].isdigit():
            return f"task_{int(value[5:])}"

        if value.startswith("task") and value[4:].isdigit():
            return f"task_{int(value[4:])}"

        # Handle LLM-generated shorthand IDs: T1, T2, T3 → task_1, task_2, task_3
        if len(value) >= 2 and value[0].upper() == "T" and value[1:].isdigit():
            return f"task_{int(value[1:])}"

        if value in known_by_name:
            return known_by_name[value]

        raise ValueError(
            f"Unknown planner dependency '{value}' "
            f"for '{task_id}'."
        )



    def _normalize_task_contract(
        self,
        task_data: dict,
        intelligence_context: dict,
    ) -> dict:
        """
        Normalize planner output against executable capability contracts.

        The planner is responsible for proposing a workflow, but the planning
        service is responsible for ensuring that the proposed workflow matches
        the framework's capability semantics.

        In particular:
        - repository_workspace acquires/prepares an execution workspace.
        - repository performs semantic repository operations.
        """

        normalized = dict(task_data)

        capability = normalized.get("capability") or normalized.get("action")
        context = normalized.get("context")

        if not isinstance(context, dict):
            context = {}

        repository_capability = "repository"
        workspace_capability = "repository_workspace"

        available_names = self._action_names

        # Only normalize when both repository capabilities actually exist.
        if (
            capability == repository_capability
            and workspace_capability in available_names
        ):
            operation = context.get("operation")

            if isinstance(operation, str):
                operation = operation.strip().lower()

            acquisition_operations = {
                "clone",
                "checkout",
                "fetch",
                "pull",
                "acquire",
            }

            semantic_repository_operations = {
                "inspect",
                "read",
                "search",
                "modify",
                "validate",
                "diff",
                "branch",
                "commit",
                "push",
                "pull_request",
            }

            # Repository acquisition belongs to repository_workspace.
            if operation in acquisition_operations:
                normalized["capability"] = workspace_capability

                context.pop("operation", None)
                normalized["context"] = context

                return normalized

            # A repository task without an explicit semantic operation is
            # ambiguous. When the workflow is executing tests from a
            # repository, interpret it as workspace acquisition.
            if not operation:
                intent = intelligence_context.get("intent")

                if isinstance(intent, str):
                    intent = intent.strip().lower()

                if intent in {
                    "execute_tests",
                    "test_execution",
                    "run_tests",
                }:
                    normalized["capability"] = workspace_capability
                    normalized["context"] = context

                    return normalized

            # Any non-empty operation that wasn't handled above is a semantic
            # repository task. Route it to the repository capability regardless
            # of whether the string is in the known set — the RepositoryAgent
            # maps the intent to whatever MCP tools are available at runtime.
            if operation:
                normalized["capability"] = repository_capability
                normalized["context"] = context

        normalized["context"] = context

        return normalized





    def _validate_plan(self, plan: Plan) -> None:

        task_ids = {
            task.task_id
            for task in plan.tasks
        }

        tasks_by_id = {
            task.task_id: task
            for task in plan.tasks
        }

        for task in plan.tasks:

            spec = self._action_specs.get(task.capability)

            if spec is None:
                raise ValueError(
                    f"No ActionSpec found for action "
                    f"'{task.capability}'."
                )

            unknown_dependencies = (
                set(task.depends_on) - task_ids
            )

            if unknown_dependencies:
                raise ValueError(
                    f"Task '{task.task_id}' has unknown "
                    "dependencies: "
                    f"{sorted(unknown_dependencies)}"
                )

            produced_by_dependencies: set[str] = set()

            for dependency_id in task.depends_on:

                dependency = tasks_by_id[dependency_id]

                dependency_spec = self._action_specs.get(
                    dependency.capability
                )

                if dependency_spec is None:
                    raise ValueError(
                        f"No ActionSpec found for dependency "
                        f"action '{dependency.capability}'."
                    )

                produced_by_dependencies.update(
                    dependency_spec.produces
                )

            missing_requirements = (
                set(spec.requires)
                - produced_by_dependencies
            )

            unresolved_requirements = {
                requirement
                for requirement in missing_requirements
                if not self._has_direct_requirement(
                    task=task,
                    requirement=requirement,
                )
            }

            if unresolved_requirements:
                raise ValueError(
                    f"Task '{task.task_id}' "
                    f"({task.capability}) is missing required "
                    "inputs: "
                    f"{sorted(unresolved_requirements)}"
                )

    @staticmethod
    def _has_direct_requirement(
        task: Task,
        requirement: str,
    ) -> bool:

        context = task.context or {}

        if requirement in context:
            value = context.get(requirement)

            return value is not None and value != ""

        return False

    @staticmethod
    def _get_intelligence_context(
        intelligence,
    ) -> dict:

        if intelligence is None:
            return {}

        context = getattr(
            intelligence,
            "context",
            None,
        )

        return (
            dict(context)
            if isinstance(context, dict)
            else {}
        )



    def _build_task_context(
        self,
        requirement,
        intelligence_context: dict,
        planner_context: dict,
    ) -> dict:
        task_context = {}

        if isinstance(intelligence_context, dict):
            task_context.update(intelligence_context)

        task_context["requirement"] = requirement

        if isinstance(planner_context, dict):
            task_context.update(planner_context)

        return task_context


    def _extract_repository_url(self, requirement) -> str | None:
        """
        Extract a repository URL from the requirement when repository
        interaction is explicitly part of the requirement.

        This is deliberately limited to URL extraction. The planner remains
        responsible for deciding whether repository interaction is required.
        """

        if not isinstance(requirement, str):
            return None

        url_pattern = r"https?://[^\s]+"

        matches = re.findall(url_pattern, requirement)

        for url in matches:
            url = url.rstrip(".,);]}>")

            if (
                "github.com/" in url
                or "gitlab.com/" in url
                or "bitbucket.org/" in url
            ):
                return url

        return None


    def _ensure_repository_workspace_context(
    self,
    task_data: dict,
    requirement,
    intelligence_context: dict,
) -> dict | None:
        """
        Ensure repository_workspace has valid repository information.

        repository_workspace is only valid when an existing repository
        was explicitly supplied.

        Generated automation workflows are allowed to proceed without
        repository information, so repository_workspace is skipped in
        that scenario.
        """

        capability = (
            task_data.get("capability")
            or task_data.get("action")
        )

        # repository_analysis is only valid when a real workspace exists.
        # Skip it when the planner adds it for a non-repository requirement
        # (workspace would be a template literal or absent entirely).
        if capability == "repository_analysis":
            ctx = task_data.get("context") or {}
            workspace = ctx.get("workspace") or ctx.get("workspace_path") or ""
            has_real_workspace = (
                isinstance(workspace, str)
                and workspace
                and "{{" not in workspace
                and not workspace.startswith("$")
            )
            has_repo = bool(
                isinstance(intelligence_context, dict)
                and (
                    intelligence_context.get("repository_url")
                    or intelligence_context.get("repository_path")
                    # Also detect any absolute path/URL stored under any key
                    # (model may use workspace, data_path, test_location, etc.)
                    or any(
                        isinstance(v, str) and (
                            (len(v) > 2 and v[1] == ":" and v[2] in "/\\")
                            or v.startswith("/")
                            or v.startswith("http://")
                            or v.startswith("https://")
                            or v.startswith("git@")
                        )
                        for v in intelligence_context.values()
                        if isinstance(v, str)
                    )
                )
            )
            if not has_real_workspace and not has_repo:
                return None

        # Only repository_workspace requires the validation below.
        if capability != "repository_workspace":
            return task_data

        repository_path = None
        repository_url = None
        branch = None

        # ---------------------------------------------------------
        # 1. Requirement intelligence
        # ---------------------------------------------------------

        if isinstance(intelligence_context, dict):
            repository_path = intelligence_context.get(
                "repository_path"
            )

            repository_url = intelligence_context.get(
                "repository_url"
            )

            branch = intelligence_context.get(
                "branch"
            )

        # ---------------------------------------------------------
        # 2. Planner-generated task context
        #
        # Planner context has higher specificity than the general
        # intelligence context.
        # ---------------------------------------------------------

        task_context = task_data.get("context")

        if isinstance(task_context, dict):

            repository_path = (
                task_context.get("repository_path")
                or repository_path
            )

            repository_url = (
                task_context.get("repository_url")
                or repository_url
            )

            branch = (
                task_context.get("branch")
                or branch
            )

        # ---------------------------------------------------------
        # 3. Extract repository URL directly from requirement
        #
        # This is only a fallback. We do not decide whether the
        # repository is needed here.
        # ---------------------------------------------------------

        if not repository_url:
            repository_url = self._extract_repository_url(
                requirement
            )

        # ---------------------------------------------------------
        # 4. No repository
        #
        # This is NOT an error.
        #
        # The workflow may be generating a new automation project.
        # ---------------------------------------------------------

        if not repository_path and not repository_url:
            return None

        # ---------------------------------------------------------
        # 5. Repository exists
        # ---------------------------------------------------------

        context = dict(task_context or {})

        context.update(
            {
                "repository_path": repository_path,
                "repository_url": repository_url,
                "branch": branch,
            }
        )

        repository = context.get("repository")

        if not isinstance(repository, dict):
            repository = {}

        if repository_url:
            repository["url"] = repository_url

        if repository_path:
            repository["path"] = repository_path

        if branch:
            repository["branch"] = branch

        context["repository"] = repository

        task_data["context"] = context

        return task_data