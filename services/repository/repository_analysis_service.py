from pathlib import Path
from typing import Any

from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from ai.services.ai_service import AIService
from constants.agent_names import AgentNames
from models.repository_execution_profile import (
    ExecutionCommand,
    RepositoryExecutionProfile,
    SuiteCandidate,
)
from utils.logger import logger


class RepositoryAnalysisService:
    """
    Analyzes an execution workspace and produces a structured
    RepositoryExecutionProfile.

    This service intentionally does not decide:
        - which framework the repository uses
        - which test runner should be used
        - which test locations should be executed
        - which suite should be selected
        - which execution command should be used

    Those decisions belong to the Repository Analysis Agent.

    This service only:
        - discovers the repository structure
        - exposes repository paths as structural evidence
        - extracts important repository-level evidence
        - builds the analysis prompt
        - calls AIService
        - validates the structured response
        - creates RepositoryExecutionProfile
    """

    MAX_FILE_SIZE = 200_000

    # Maximum number of repository-level files whose CONTENT
    # is included in the LLM evidence.
    MAX_EVIDENCE_FILES = 16

    # Maximum characters of repository-level file content.
    MAX_EVIDENCE_CHARACTERS = 12_000

    # Maximum number of paths exposed in repository structure.
    #
    # These are PATHS ONLY. No source/test-file content is read
    # into this section.
    MAX_STRUCTURE_PATHS = 500

    IGNORED_DIRECTORIES = {
        ".git",
        ".qagentic",
        ".idea",
        ".vscode",
        "node_modules",
        "target",
        "build",
        "dist",
        "__pycache__",
        ".gradle",
    }

    IMPORTANT_ROOT_FILES = {
        "readme",
        "readme.md",
        "readme.txt",
        "readme.rst",
        "contributing",
        "contributing.md",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        "pom.xml",
        "package.json",
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "setup.py",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        "cargo.toml",
        "go.mod",
        "go.sum",
        "gemfile",
        "gemfile.lock",
        "composer.json",
        "composer.lock",
    }

    IMPORTANT_FILE_NAMES = {
        "testng.xml",
        "junit-platform.properties",
        "junit-platform.yaml",
        "junit-platform.yml",
        "cucumber.properties",
        "cucumber.yml",
        "cucumber.yaml",
        "playwright.config.js",
        "playwright.config.ts",
        "playwright.config.mjs",
        "playwright.config.cjs",
        "playwright.config.cts",
        "playwright.config.mts",
        "webpack.config.js",
        "webpack.config.ts",
        "tsconfig.json",
        "jsconfig.json",
    }

    IMPORTANT_FILE_PREFIXES = (
        "playwright.config.",
    )

    IMPORTANT_DIRECTORY_NAMES = {
        "config",
        "configuration",
        "configs",
        "settings",
        "resources",
        "scripts",
    }

    TEST_LIKE_DIRECTORY_NAMES = {
        "test",
        "tests",
        "testing",
        "spec",
        "specs",
        "e2e",
        "integration",
        "functional",
        "acceptance",
        "qa",
        "automation",
    }

    def __init__(
        self,
        ai_service: AIService,
        prompt_builder: PromptBuilder,
    ) -> None:
        self.ai_service = ai_service
        self.prompt_builder = prompt_builder

    def analyze(
        self,
        workspace_path: str,
        requested_suite: str | None = None,
    ) -> RepositoryExecutionProfile:
        if not workspace_path:
            raise ValueError(
                "Repository analysis requires a workspace path."
            )

        workspace = Path(workspace_path).resolve()

        if not workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise NotADirectoryError(
                f"Workspace is not a directory: {workspace}"
            )

        evidence = self._collect_evidence(workspace)

        prompt = self.prompt_builder.repository_analysis(
            workspace_path=str(workspace),
            repository_evidence=evidence,
            requested_suite=requested_suite,
        )

        request = LLMRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
        )

        response = self.ai_service.generate_json(
            AgentNames.REPOSITORY_ANALYSIS,
            request,
        )

        return self._build_profile(
            response=response,
            workspace_path=str(workspace),
            requested_suite=requested_suite,
        )

    def _collect_evidence(
        self,
        workspace: Path,
    ) -> dict[str, Any]:
        discovered_files = list(
            self._iter_files(workspace)
        )

        repository_structure = (
            self._build_repository_structure(
                workspace,
                discovered_files,
            )
        )

        selected_paths = self._select_repository_artifacts(
            workspace,
            discovered_files,
        )

        files: list[dict[str, Any]] = []
        total_characters = 0

        for path in selected_paths:
            content = self._read_text_file(path)

            if content is None:
                continue

            remaining = (
                self.MAX_EVIDENCE_CHARACTERS
                - total_characters
            )

            if remaining <= 0:
                break

            if len(content) > remaining:
                content = self._trim_content(
                    content,
                    remaining,
                )

            if not content:
                continue

            relative_path = path.relative_to(workspace)

            files.append(
                {
                    "path": str(relative_path),
                    "content": content,
                }
            )

            total_characters += len(content)

        logger.info(
            "Repository analysis evidence | "
            "workspace=%s | discovered_files=%d | "
            "selected_files=%d",
            workspace,
            len(discovered_files),
            len(files),
        )

        logger.info(
            "Repository analysis evidence files | "
            "selected=%s",
            [
                item["path"]
                for item in files
            ],
        )

        logger.info(
            "Repository analysis structure | "
            "directories=%d | files=%d | "
            "test_like_paths=%d",
            len(
                repository_structure["directories"]
            ),
            len(
                repository_structure["files"]
            ),
            len(
                repository_structure["test_like_paths"]
            ),
        )

        logger.info(
            "Repository analysis evidence size | "
            "characters=%d | budget=%d",
            total_characters,
            self.MAX_EVIDENCE_CHARACTERS,
        )

        return {
            "workspace": str(workspace),
            "repository_structure": repository_structure,
            "files": files,
        }

    def _build_repository_structure(
        self,
        workspace: Path,
        discovered_files: list[Path],
    ) -> dict[str, list[str]]:
        """
        Builds structural repository evidence.

        IMPORTANT:
            This method exposes PATHS ONLY.

        It does not read test source files or application
        source files.

        The purpose is to allow the Repository Analysis Agent
        to determine:
            - test locations
            - source locations
            - configuration locations
            - repository layout

        without sending source-code content to the LLM.
        """

        directories: set[str] = set()
        files: list[str] = []

        for path in discovered_files:
            relative_path = path.relative_to(workspace)

            relative_parts = relative_path.parts

            for index in range(
                1,
                len(relative_parts),
            ):
                directory = Path(
                    *relative_parts[:index]
                )

                directories.add(
                    str(directory)
                )

            files.append(
                str(relative_path)
            )

        sorted_directories = sorted(
            directories,
            key=lambda value: (
                value.count("/"),
                value.lower(),
            ),
        )

        sorted_files = sorted(
            files,
            key=lambda value: value.lower(),
        )

        test_like_paths = sorted(
            {
                path
                for path in sorted_files
                if self._is_test_like_path(path)
            },
            key=lambda value: value.lower(),
        )

        # Keep structural evidence bounded.
        #
        # Prefer test-like paths because they are particularly
        # useful to the agent for identifying test locations.
        bounded_test_like_paths = test_like_paths[
            : self.MAX_STRUCTURE_PATHS
        ]

        bounded_files = sorted_files[
            : self.MAX_STRUCTURE_PATHS
        ]

        return {
            "directories": sorted_directories[
                : self.MAX_STRUCTURE_PATHS
            ],
            "files": bounded_files,
            "test_like_paths": bounded_test_like_paths,
        }

    def _is_test_like_path(
        self,
        relative_path: str,
    ) -> bool:
        parts = Path(
            relative_path
        ).parts

        return any(
            part.lower()
            in self.TEST_LIKE_DIRECTORY_NAMES
            for part in parts[:-1]
        )

    def _select_repository_artifacts(
        self,
        workspace: Path,
        paths: list[Path],
    ) -> list[Path]:
        selected: list[Path] = []
        selected_keys: set[str] = set()

        def add(path: Path) -> None:
            if len(selected) >= self.MAX_EVIDENCE_FILES:
                return

            key = str(
                path.relative_to(workspace)
            ).lower()

            if key in selected_keys:
                return

            selected.append(path)
            selected_keys.add(key)

        root_files = sorted(
            (
                path
                for path in paths
                if len(
                    path.relative_to(workspace).parts
                ) == 1
            ),
            key=lambda path: path.name.lower(),
        )

        for path in root_files:
            filename = path.name.lower()

            if filename in self.IMPORTANT_ROOT_FILES:
                add(path)

        important_files = sorted(
            (
                path
                for path in paths
                if path.name.lower()
                in self.IMPORTANT_FILE_NAMES
                or any(
                    path.name.lower().startswith(prefix)
                    for prefix in self.IMPORTANT_FILE_PREFIXES
                )
            ),
            key=lambda path: (
                len(
                    path.relative_to(workspace).parts
                ),
                str(path).lower(),
            ),
        )

        for path in important_files:
            add(path)

        configuration_files = sorted(
            (
                path
                for path in paths
                if self._is_repository_configuration_file(
                    path,
                    workspace,
                )
            ),
            key=lambda path: (
                len(
                    path.relative_to(workspace).parts
                ),
                str(path).lower(),
            ),
        )

        for path in configuration_files:
            add(path)

        if not selected:
            for path in root_files:
                if self._is_metadata_file(path):
                    add(path)

                if len(selected) >= self.MAX_EVIDENCE_FILES:
                    break

        return selected

    def _is_repository_configuration_file(
        self,
        path: Path,
        workspace: Path,
    ) -> bool:
        relative_path = path.relative_to(workspace)

        parts = [
            part.lower()
            for part in relative_path.parts
        ]

        excluded_directory_names = {
            "test",
            "tests",
            "spec",
            "specs",
            "src",
            "source",
            "main",
        }

        if any(
            part in excluded_directory_names
            for part in parts[:-1]
        ):
            return False

        if any(
            part in self.IMPORTANT_DIRECTORY_NAMES
            for part in parts[:-1]
        ):
            return self._looks_like_configuration_file(
                path
            )

        return False

    def _looks_like_configuration_file(
        self,
        path: Path,
    ) -> bool:
        filename = path.name.lower()
        suffix = path.suffix.lower()

        configuration_suffixes = {
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".properties",
        }

        if suffix in configuration_suffixes:
            return True

        configuration_terms = {
            "config",
            "configuration",
            "settings",
            "environment",
            "env",
            "setup",
        }

        return any(
            term in filename
            for term in configuration_terms
        )

    @staticmethod
    def _is_metadata_file(
        path: Path,
    ) -> bool:
        filename = path.name.lower()

        return (
            filename.startswith("readme")
            or filename.startswith("contributing")
            or filename in {
                ".gitignore",
                ".dockerignore",
                "docker-compose.yml",
                "docker-compose.yaml",
                "compose.yml",
                "compose.yaml",
            }
        )

    def _iter_files(
        self,
        workspace: Path,
    ):
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue

            relative_path = path.relative_to(
                workspace
            )

            if any(
                part.lower()
                in self.IGNORED_DIRECTORIES
                for part in relative_path.parts
            ):
                continue

            yield path

    def _read_text_file(
        self,
        path: Path,
    ) -> str | None:
        try:
            if path.stat().st_size > self.MAX_FILE_SIZE:
                return None

            return path.read_text(
                encoding="utf-8"
            )

        except (
            OSError,
            UnicodeDecodeError,
        ):
            return None

    @staticmethod
    def _trim_content(
        content: str,
        maximum_characters: int,
    ) -> str:
        if len(content) <= maximum_characters:
            return content

        if maximum_characters <= 200:
            return content[:maximum_characters]

        marker = (
            "\n\n"
            "[...file content truncated because "
            "of repository evidence budget...]\n\n"
        )

        available = (
            maximum_characters
            - len(marker)
        )

        if available <= 0:
            return content[:maximum_characters]

        head_size = int(
            available * 0.70
        )

        tail_size = (
            available
            - head_size
        )

        return (
            content[:head_size]
            + marker
            + content[-tail_size:]
        )

    def _build_profile(
        self,
        response: dict[str, Any],
        workspace_path: str,
        requested_suite: str | None,
    ) -> RepositoryExecutionProfile:
        if not isinstance(
            response,
            dict,
        ):
            raise ValueError(
                "Repository analysis response must be an object."
            )

        profile = RepositoryExecutionProfile(
            project_types=self._string_list(
                response.get("project_types")
            ),
            frameworks=self._string_list(
                response.get("frameworks")
            ),
            test_locations=self._string_list(
                response.get("test_locations")
            ),
            configuration_files=self._string_list(
                response.get("configuration_files")
            ),
            runner_candidates=self._string_list(
                response.get("runner_candidates")
            ),
            working_directory=workspace_path,
            requested_suite=requested_suite,
        )

        for raw_suite in response.get(
            "suite_candidates",
            [],
        ):
            try:
                candidate = (
                    self._parse_suite_candidate(
                        raw_suite
                    )
                )

            except ValueError as exc:
                logger.warning(
                    "Ignoring malformed suite candidate | "
                    "error=%s | value=%s",
                    exc,
                    raw_suite,
                )
                continue

            profile.add_suite_candidate(
                candidate
            )

        for raw_command in response.get(
            "execution_commands",
            [],
        ):
            try:
                command = (
                    self._parse_execution_command(
                        raw_command
                    )
                )

            except ValueError as exc:
                logger.warning(
                    "Ignoring malformed execution command | "
                    "error=%s | value=%s",
                    exc,
                    raw_command,
                )
                continue

            profile.add_execution_command(
                command
            )

        selected_framework = response.get(
            "selected_framework"
        )

        if isinstance(
            selected_framework,
            str,
        ):
            profile.selected_framework = (
                selected_framework.strip()
                or None
            )

        selected_runner = response.get(
            "selected_runner"
        )

        if isinstance(
            selected_runner,
            str,
        ):
            profile.selected_runner = (
                selected_runner.strip()
                or None
            )

        profile.deterministic = bool(
            response.get(
                "deterministic",
                False,
            )
        )

        confidence = response.get(
            "confidence",
            0.0,
        )

        if isinstance(
            confidence,
            (int, float),
        ):
            profile.confidence = max(
                0.0,
                min(
                    1.0,
                    float(confidence),
                ),
            )

        metadata = response.get(
            "metadata",
            {},
        )

        profile.metadata = (
            metadata
            if isinstance(
                metadata,
                dict,
            )
            else {}
        )
        selected_suite = response.get(
            "selected_suite"
        )

        if isinstance(
            selected_suite,
            str,
        ) and selected_suite.strip():
            profile.select_suite(
                selected_suite.strip()
            )

        elif isinstance(
            selected_suite,
            dict,
        ):
            selected_suite_name = selected_suite.get(
                "name"
            )

            if isinstance(
                selected_suite_name,
                str,
            ) and selected_suite_name.strip():
                profile.select_suite(
                    selected_suite_name.strip()
                )
        if requested_suite:
            profile.select_suite(
                requested_suite
            )

        return profile

    @staticmethod
    def _parse_suite_candidate(
        value: Any,
    ) -> SuiteCandidate:
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "Each suite candidate must be an object."
            )

        name = value.get("name")
        mechanism = value.get("mechanism")

        if not isinstance(
            name,
            str,
        ) or not name.strip():
            raise ValueError(
                "Suite candidate requires a name."
            )

        if not isinstance(
            mechanism,
            str,
        ) or not mechanism.strip():
            raise ValueError(
                "Suite candidate requires a mechanism."
            )

        command = None

        raw_command = value.get(
            "command"
        )

        if isinstance(
            raw_command,
            dict,
        ):
            executable = raw_command.get(
                "executable"
            )

            # A suite candidate does not require an
            # execution command. The command may be
            # determined later by the execution planner.
            #
            # Therefore:
            #   command = None
            #
            # is valid when the LLM provides a command
            # object without an executable.
            if (
                isinstance(
                    executable,
                    str,
                )
                and executable.strip()
            ):
                command = (
                    RepositoryAnalysisService
                    ._parse_execution_command(
                        raw_command
                    )
                )

        elif raw_command is not None:
            command = (
                RepositoryAnalysisService
                ._parse_execution_command(
                    raw_command
                )
            )

        confidence = value.get(
            "confidence",
            0.0,
        )

        try:
            parsed_confidence = float(
                confidence
            )

        except (
            TypeError,
            ValueError,
        ):
            parsed_confidence = 0.0

        metadata = value.get(
            "metadata",
            {},
        )

        return SuiteCandidate(
            name=name.strip(),
            mechanism=mechanism.strip(),
            selector=value.get(
                "selector"
            ),
            source=value.get(
                "source"
            ),
            command=command,
            deterministic=bool(
                value.get(
                    "deterministic",
                    False,
                )
            ),
            confidence=max(
                0.0,
                min(
                    1.0,
                    parsed_confidence,
                ),
            ),
            metadata=(
                metadata
                if isinstance(
                    metadata,
                    dict,
                )
                else {}
            ),
        )

    @staticmethod
    def _parse_execution_command(
        value: Any,
    ) -> ExecutionCommand:
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "Execution command must be an object."
            )

        executable = value.get(
            "executable"
        )

        if not isinstance(
            executable,
            str,
        ) or not executable.strip():
            raise ValueError(
                "Execution command requires an executable."
            )

        arguments = value.get(
            "arguments",
            [],
        )

        if not isinstance(
            arguments,
            list,
        ) or not all(
            isinstance(
                argument,
                str,
            )
            for argument in arguments
        ):
            raise ValueError(
                "Execution command arguments "
                "must be a list of strings."
            )

        return ExecutionCommand(
            executable=executable.strip(),
            arguments=list(arguments),
            description=str(
                value.get(
                    "description",
                    "",
                )
            ),
            suite=value.get(
                "suite"
            ),
        )

    @staticmethod
    def _string_list(
        value: Any,
    ) -> list[str]:
        if not isinstance(
            value,
            list,
        ):
            return []

        return [
            item.strip()
            for item in value
            if isinstance(
                item,
                str,
            )
            and item.strip()
        ]