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

        tasks_data = response.get("tasks")

        if not isinstance(tasks_data, list) or not tasks_data:
            raise ValueError(
                "Planner response must contain a non-empty 'tasks' list."
            )

        plan = Plan()

        intelligence_context = self._get_intelligence_context(
            intelligence
        )
        skipped_task_ids: set[str] = set()

        for index, raw_task_data in enumerate(tasks_data, start=1):
            if not isinstance(raw_task_data, dict):
                raise ValueError(
                    f"Planner task at index {index} must be an object."
                )

            task_data = self._normalize_task_contract(
                raw_task_data,
                intelligence_context,
            )

            task_data = self._ensure_repository_workspace_context(
                    task_data=task_data,
                    requirement=requirement,
                    intelligence_context=intelligence_context,
                )

                # ---------------------------------------------------------
                # A repository_workspace task is only valid when an actual
                # repository source was supplied.
                #
                # If no repository exists, this task is intentionally skipped.
                # This allows generated-automation workflows to proceed without
                # an existing repository.
                # ---------------------------------------------------------

            if task_data is None:
                    skipped_task_ids.add(f"task_{index}")
                    continue

            action_name = (
                    task_data.get("capability")
                    or task_data.get("action")
                )

            if action_name not in self._action_names:
                raise ValueError(
                    "Planner returned unsupported executable action: "
                    f"{action_name}"
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
                task_id=f"task_{index}",
                capability=action_name,
                description=description.strip(),
                context=task_context,
                depends_on=[],
            )

            raw_dependencies = task_data.get(
                "depends_on",
                [],
            )

            if not isinstance(raw_dependencies, list):
                raw_dependencies = [raw_dependencies]

            raw_dependencies = [
                dependency
                for dependency in raw_dependencies
                if self._dependency_task_id(dependency) not in skipped_task_ids
            ]

            task.depends_on = self._normalize_dependencies(
                task_id=task.task_id,
                raw_dependencies=raw_dependencies,
                planned_tasks=plan.tasks,
            )

            plan.tasks.append(task)

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
            return normalized
        if normalized.startswith("task") and normalized[4:].isdigit():
            return f"task_{normalized[4:]}"
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
            return value

        if value.startswith("task") and value[4:].isdigit():
            return f"task_{value[4:]}"

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

            # Explicit semantic repository operations remain repository tasks.
            if operation in semantic_repository_operations:
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

        # Only repository_workspace requires this validation.
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