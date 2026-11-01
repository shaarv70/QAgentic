import os
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
        - exposes compact repository evidence (paths only, no source)
        - extracts important repository-level file contents
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

    # Maximum characters included from any single file so that one large
    # file (e.g. a package.json with many scripts) cannot crowd out smaller
    # but more informative files (e.g. playwright.config.ts).
    MAX_FILE_EVIDENCE_CHARACTERS = 3_000

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
        "test-results",
        "playwright-report",
        "allure-results",
        "allure-report",
        "coverage",
        ".nyc_output",
        "reports",
        "out",
        "bin",
        ".cache",
        ".npm",
        ".yarn",
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
        "gemfile",
        "composer.json",
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

    # File suffixes/patterns that identify test source files.
    TEST_FILE_SUFFIXES = (
        ".spec.ts", ".spec.js", ".spec.mjs", ".spec.cjs",
        ".test.ts", ".test.js", ".test.mjs",
        "_test.py", "test_.py",
        ".feature",
        "Test.java", "Tests.java",
        ".Test.cs", ".Tests.cs",
    )

    # Hard cap on test file paths included in evidence (paths only, no content).
    MAX_TEST_FILES_IN_EVIDENCE = 60

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

        profile = self._build_profile(
            response=response,
            workspace_path=str(workspace),
            requested_suite=requested_suite,
        )

        structure = evidence["repository_structure"]
        test_files = structure.get("test_files", [])

        # Deterministic fallback: use test_like_dirs when the LLM did not
        # populate test_locations despite the evidence containing them.
        if not profile.test_locations:
            profile.test_locations = list(
                structure.get("test_like_dirs", [])
            )

        # Deterministic fallback: build suite_candidates + execution_commands
        # from the evidence when the LLM left them empty.  The LLM already
        # identified the framework and runner; this step is mechanical assembly.
        if test_files and (
            not profile.suite_candidates
            or not profile.execution_commands
        ):
            self._apply_deterministic_suite_fallback(
                profile,
                test_files,
                requested_suite,
            )

        # Deterministic fallback: re-apply confidence/deterministic defaults.
        if profile.execution_commands and not profile.deterministic:
            profile.deterministic = True
        if profile.confidence == 0.0 and (
            profile.frameworks or profile.test_locations
        ):
            profile.confidence = 0.8

        return profile

    # Maps lowercase framework name fragments to the CLI runner command
    # used to invoke that framework.  The service never interprets which
    # framework is present — that came from the LLM.  This table only
    # converts a known name to its CLI so commands can be assembled
    # without another LLM call.
    _FRAMEWORK_CLI: dict[str, str] = {
        "playwright": "npx playwright test",
        "jest": "npx jest",
        "vitest": "npx vitest",
        "mocha": "npx mocha",
        "jasmine": "npx jasmine",
        "cypress": "npx cypress run",
        "pytest": "python -m pytest",
        "unittest": "python -m pytest",
        "robot": "robot",
        "testng": "mvn test",
        "junit": "mvn test",
        "maven": "mvn test",
        "gradle": "./gradlew test",
        "dotnet": "dotnet test",
        "xunit": "dotnet test",
        "nunit": "dotnet test",
        "rspec": "bundle exec rspec",
        "go": "go test",
    }

    def _resolve_runner_cli(
        self,
        profile: "RepositoryExecutionProfile",
    ) -> str | None:
        """
        Return the best CLI runner string for the profile.

        Priority:
          1. First execution_command already on the profile (reuse its executable).
          2. runner_candidates that look like a runnable command (not a package).
          3. Lookup in _FRAMEWORK_CLI using identified frameworks.
        """
        if profile.execution_commands:
            cmd = profile.execution_commands[0]
            return f"{cmd.executable} {' '.join(cmd.arguments[:2])}".strip()

        for rc in profile.runner_candidates:
            # Skip bare npm package identifiers like "@playwright/test"
            if rc and not rc.startswith("@") and "/" not in rc:
                return rc

        for fw in profile.frameworks:
            fw_lower = fw.lower()
            for key, cli in self._FRAMEWORK_CLI.items():
                if key in fw_lower:
                    return cli

        return None

    def _apply_deterministic_suite_fallback(
        self,
        profile: "RepositoryExecutionProfile",
        test_files: list[str],
        requested_suite: str | None,
    ) -> None:
        """
        Build suite_candidates and execution_commands from test_files when
        the LLM left them empty.

        This is MECHANICAL ASSEMBLY only — it combines the LLM's identified
        runner with the deterministic file list to produce structured objects.
        No framework interpretation is performed here.
        """
        from pathlib import PurePosixPath

        runner_cli = self._resolve_runner_cli(profile)
        if not runner_cli:
            return

        # Parse the runner into executable + base args
        import shlex as _shlex
        try:
            runner_parts = _shlex.split(runner_cli)
        except ValueError:
            runner_parts = runner_cli.split()
        if not runner_parts:
            return

        executable = runner_parts[0]
        base_args = runner_parts[1:]

        for rel_path in test_files:
            normalized = rel_path.replace("\\", "/")
            stem = PurePosixPath(normalized).stem
            # Strip common test suffixes: .spec, .test, .e2e
            for sfx in (".spec", ".test", ".e2e"):
                if stem.lower().endswith(sfx):
                    stem = stem[: -len(sfx)]
                    break

            cmd = ExecutionCommand(
                executable=executable,
                arguments=base_args + [normalized],
                description=f"Run {stem}",
                suite=stem,
            )

            candidate = SuiteCandidate(
                name=stem,
                mechanism="spec_file",
                selector=normalized,
                source=normalized,
                command=cmd,
                deterministic=True,
                confidence=0.85,
            )

            profile.add_suite_candidate(candidate)
            profile.add_execution_command(cmd)

        # If a specific suite was requested, try to select it now
        if requested_suite and not profile.selected_suite:
            profile.select_suite(requested_suite)
            if not profile.selected_suite:
                profile.set_selected_suite(requested_suite)

        logger.info(
            "Deterministic suite fallback applied | "
            "test_files=%d | runner=%s | suite_candidates=%d",
            len(test_files),
            runner_cli,
            len(profile.suite_candidates),
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

            limit = min(remaining, self.MAX_FILE_EVIDENCE_CHARACTERS)

            if len(content) > limit:
                content = self._trim_content(
                    content,
                    limit,
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
            "directories=%d | test_like_dirs=%d | "
            "root_files=%d | test_files=%d",
            len(repository_structure["directories"]),
            len(repository_structure["test_like_dirs"]),
            len(repository_structure["root_files"]),
            len(repository_structure["test_files"]),
        )

        logger.info(
            "Repository analysis evidence size | "
            "file_content_chars=%d | budget=%d",
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
        Builds compact structural repository evidence.

        IMPORTANT:
            This method exposes PATHS ONLY — no file contents.

        Evidence returned:

            directories:
                Every directory path discovered in the workspace.
                Allows the agent to understand the overall layout
                (source roots, resource locations, depth, etc.).

            test_like_dirs:
                Directory paths that reside inside or are themselves
                test-oriented (e.g. "src/test/java", "tests/e2e").
                These can be used DIRECTLY as test_locations by the
                agent without any further extraction step.

            root_files:
                Filenames present at the repository root.
                The agent can identify the build system and framework
                from names like "pom.xml", "testng.xml", "package.json"
                even when their full content is not included.
        """

        directories: set[str] = set()
        root_file_names: list[str] = []

        for path in discovered_files:
            relative_path = path.relative_to(workspace)
            relative_parts = relative_path.parts

            # Collect every ancestor directory.
            for index in range(1, len(relative_parts)):
                directory = Path(*relative_parts[:index])
                directories.add(str(directory))

            # Collect root-level file names.
            if len(relative_parts) == 1:
                root_file_names.append(relative_parts[0])

        sorted_directories = sorted(
            directories,
            key=lambda value: (
                value.count("/"),
                value.lower(),
            ),
        )

        # test_like_dirs: directories (not file paths) whose path
        # contains a test-oriented component.  These represent the
        # actual directories that contain test code and can be used
        # directly as test_locations.
        test_like_dirs = sorted(
            {
                d
                for d in sorted_directories
                if self._is_test_like_dir(d)
            },
            key=lambda value: value.lower(),
        )

        # test_files: relative paths of files that look like test sources
        # (e.g. *.spec.ts, *.test.ts, *_test.py, *.feature) that reside
        # inside a test_like_dir.  PATHS ONLY — no file contents.
        # Gives the agent the full suite list without requiring it to
        # "read" files it cannot access.
        test_like_dir_set = {
            d.replace("\\", "/")
            for d in test_like_dirs
        }
        test_files: list[str] = []
        for path in discovered_files:
            rel = str(
                path.relative_to(workspace)
            ).replace("\\", "/")
            parent = "/".join(rel.split("/")[:-1])
            if (
                parent in test_like_dir_set
                and self._is_test_file(path.name)
            ):
                test_files.append(rel)
            if len(test_files) >= self.MAX_TEST_FILES_IN_EVIDENCE:
                break

        return {
            "directories": sorted_directories[
                : self.MAX_STRUCTURE_PATHS
            ],
            "test_like_dirs": test_like_dirs[
                : self.MAX_STRUCTURE_PATHS
            ],
            "root_files": sorted(root_file_names),
            "test_files": sorted(test_files),
        }

    def _is_test_like_dir(
        self,
        directory_path: str,
    ) -> bool:
        """
        Returns True when any component of the directory path
        matches a test-oriented directory name.

        Operates on directory paths only (no filename suffix to strip).
        """
        parts = Path(directory_path).parts

        return any(
            part.lower() in self.TEST_LIKE_DIRECTORY_NAMES
            for part in parts
        )

    def _is_test_file(
        self,
        filename: str,
    ) -> bool:
        """
        Returns True when the filename looks like a test source file.
        Checks known suffixes (e.g. .spec.ts, _test.py, .feature).
        """
        lower = filename.lower()
        return any(lower.endswith(s.lower()) for s in self.TEST_FILE_SUFFIXES)

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

        # Framework config files (playwright.config.ts, pom.xml, etc.) are
        # selected FIRST so they are never crowded out by larger root files
        # such as package.json.
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

        for path in root_files:
            filename = path.name.lower()

            if filename in self.IMPORTANT_ROOT_FILES:
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
        for dirpath, dirnames, filenames in os.walk(
            workspace,
            followlinks=False,
            onerror=lambda _: None,
        ):
            dirnames[:] = [
                d for d in dirnames
                if d.lower() not in self.IGNORED_DIRECTORIES
            ]

            for filename in filenames:
                path = Path(dirpath) / filename

                try:
                    relative_path = path.relative_to(workspace)
                except ValueError:
                    continue

                if any(
                    part.lower() in self.IGNORED_DIRECTORIES
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

        # Normalize common LLM alias schemas onto the expected field names
        # before attempting to build the profile.
        response = self._normalize_response(response)

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
            profile.select_suite(requested_suite)
            # Fuzzy fallback when exact-name match finds nothing
            # (e.g. suite candidate name differs by case or is a path stem).
            if not profile.selected_suite:
                profile.set_selected_suite(requested_suite)

        # Post-process: set evidence-based defaults when the LLM forgets.
        # deterministic=True when we have at least one runnable command.
        if profile.execution_commands and not profile.deterministic:
            profile.deterministic = True
        # confidence reflects actual evidence quality; 0.0 is almost never
        # correct when frameworks or test_locations were discovered.
        if profile.confidence == 0.0 and (
            profile.frameworks or profile.test_locations
        ):
            profile.confidence = 0.8

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

        if not isinstance(mechanism, str) or not mechanism.strip():
            # LLM frequently omits this field — default it rather than
            # rejecting the candidate and losing all suite information.
            mechanism = "spec_file"

        command = None

        raw_command = value.get("command")

        if isinstance(raw_command, str) and raw_command.strip():
            # LLM sometimes returns a plain command string instead of a
            # structured object.  Parse it so the command is not lost.
            import shlex as _shlex
            try:
                parts = _shlex.split(raw_command.strip())
            except ValueError:
                parts = raw_command.strip().split()
            if parts:
                command = ExecutionCommand(
                    executable=parts[0],
                    arguments=parts[1:],
                    description=f"Run {name.strip()}",
                    suite=name.strip(),
                )
        elif isinstance(
            raw_command,
            dict,
        ):
            executable = raw_command.get(
                "executable"
            )

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
    def _normalize_response(
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Map common LLM alias schemas onto the expected field names.

        The LLM sometimes returns a rich custom schema (e.g.
        ``"framework": {"name": "Playwright"}`` or
        ``"test_suites": [...]``) instead of the required
        ``"frameworks": ["Playwright"]`` / ``"suite_candidates": [...].``

        This method is SCHEMA TRANSLATION ONLY.  It never interprets
        repository semantics — it only maps one set of JSON key names
        to another so that _build_profile can populate the profile
        correctly regardless of which schema variant the LLM produced.
        """
        import shlex

        out = {**response}

        # ---- frameworks ----
        if not out.get("frameworks"):
            fw = out.get("framework") or out.get("test_framework")
            if isinstance(fw, str) and fw.strip():
                out["frameworks"] = [fw.strip()]
            elif isinstance(fw, dict):
                name = fw.get("name", "")
                if isinstance(name, str) and name.strip():
                    out["frameworks"] = [name.strip()]

        # ---- project_types ----
        if not out.get("project_types"):
            types: list[str] = []
            for key in ("language", "project_language", "stack"):
                val = out.get(key)
                if isinstance(val, str) and val.strip():
                    types.append(val.strip())
            fw = out.get("framework")
            if isinstance(fw, dict):
                lang = fw.get("language", "")
                if isinstance(lang, str) and lang.strip():
                    types.append(lang.strip())
            if types:
                out["project_types"] = list(dict.fromkeys(types))

        # ---- test_locations ----
        # Prefer directory paths over individual file paths.
        existing_locs = out.get("test_locations")
        if not existing_locs:
            for key in (
                "test_dir",
                "testDir",
                "test_directory",
                "testDirectory",
                "specDir",
                "spec_dir",
                "testsDir",
                "tests_dir",
            ):
                val = out.get(key)
                if isinstance(val, str) and val.strip():
                    out["test_locations"] = [val.strip()]
                    break
            if not out.get("test_locations"):
                fw = out.get("framework")
                if isinstance(fw, dict):
                    for key in (
                        "test_dir",
                        "testDir",
                        "test_directory",
                        "testDirectory",
                    ):
                        val = fw.get(key, "")
                        if isinstance(val, str) and val.strip():
                            out["test_locations"] = [val.strip()]
                            break
            if not out.get("test_locations"):
                # LLM sometimes nests test_dir under test_configuration.
                for tc_key in (
                    "test_configuration",
                    "testConfiguration",
                    "test_config",
                    "testConfig",
                ):
                    tc = out.get(tc_key)
                    if not isinstance(tc, dict):
                        continue
                    for key in (
                        "test_dir",
                        "testDir",
                        "test_directory",
                        "testDirectory",
                        "dir",
                    ):
                        val = tc.get(key, "")
                        if isinstance(val, str) and val.strip():
                            cleaned = (
                                val.strip().lstrip("./").strip("/")
                            )
                            if cleaned:
                                out["test_locations"] = [cleaned]
                            break
                    if out.get("test_locations"):
                        break
        else:
            # Promote file paths to their parent directory when all
            # test_locations values look like file paths (contain a dot
            # in the last path component).
            locs = [
                str(loc).replace("\\", "/")
                for loc in existing_locs
                if isinstance(loc, str)
            ]
            file_like = [
                l for l in locs
                if "." in l.split("/")[-1]
            ]
            if file_like and len(file_like) == len(locs):
                # All entries are files — extract unique parent dirs.
                from pathlib import PurePosixPath
                dirs = list(
                    dict.fromkeys(
                        str(PurePosixPath(l).parent)
                        for l in locs
                    )
                )
                if dirs:
                    out["test_locations"] = dirs

        # ---- configuration_files ----
        if not out.get("configuration_files"):
            configs: list[str] = []
            for key in ("config_file", "configFile", "config"):
                val = out.get(key)
                if isinstance(val, str) and val.strip():
                    configs.append(val.strip())
            fw = out.get("framework")
            if isinstance(fw, dict):
                for key in ("config_file", "configFile"):
                    val = fw.get(key, "")
                    if isinstance(val, str) and val.strip():
                        configs.append(val.strip())
            cfg = out.get("configuration")
            if isinstance(cfg, dict):
                for key in ("config_file", "configFile"):
                    val = cfg.get(key, "")
                    if isinstance(val, str) and val.strip():
                        configs.append(val.strip())
            if configs:
                out["configuration_files"] = list(
                    dict.fromkeys(configs)
                )

        # ---- runner_candidates ----
        if not out.get("runner_candidates"):
            candidates: list[str] = []
            for key in (
                "runner",
                "runner_command",
                "test_runner",
                "runner_cli",
                "testRunner",
            ):
                val = out.get(key)
                if isinstance(val, str) and val.strip():
                    candidates.append(val.strip())
            fw = out.get("framework")
            if isinstance(fw, dict):
                for key in ("runner", "test_runner", "testRunner"):
                    val = fw.get(key, "")
                    if isinstance(val, str) and val.strip():
                        candidates.append(val.strip())
            if candidates:
                out["runner_candidates"] = list(
                    dict.fromkeys(candidates)
                )

        # ---- suite_candidates + execution_commands from test_suites ----
        test_suites = (
            out.get("test_suites")
            or out.get("testSuites")
            or out.get("suites")
            or out.get("test_scripts")
            or out.get("testScripts")
        )

        if test_suites and isinstance(test_suites, list):
            if not out.get("suite_candidates"):
                suite_cands = []
                for ts in test_suites:
                    if not isinstance(ts, dict):
                        continue
                    name = ts.get("name", "")
                    if not isinstance(name, str) or not name.strip():
                        # Derive a name from file/path/spec stem.
                        for src_key in ("file", "path", "spec", "source", "selector"):
                            src = ts.get(src_key, "")
                            if isinstance(src, str) and src.strip():
                                from pathlib import PurePosixPath
                                stem = PurePosixPath(
                                    src.strip().replace("\\", "/")
                                ).stem
                                # Strip common suffixes like .spec, .test
                                for suffix in (".spec", ".test", ".e2e"):
                                    if stem.lower().endswith(suffix):
                                        stem = stem[: -len(suffix)]
                                        break
                                if stem:
                                    name = stem
                                break
                    if not isinstance(name, str) or not name.strip():
                        continue
                    # Parse run command string into executable + args.
                    # Expand npm script shorthand to a full command.
                    npm_script = ts.get("npmScript") or ts.get("npm_script")
                    raw_cmd = (
                        ts.get("command")
                        or ts.get("run_command")
                        or ts.get("cmd")
                    )
                    if not raw_cmd and npm_script and isinstance(npm_script, str):
                        raw_cmd = f"npm run {npm_script.strip()}"
                    cmd_str = raw_cmd
                    cmd_obj = None
                    if isinstance(cmd_str, str) and cmd_str.strip():
                        try:
                            parts = shlex.split(cmd_str.strip())
                        except ValueError:
                            parts = cmd_str.strip().split()
                        if parts:
                            cmd_obj = {
                                "executable": parts[0],
                                "arguments": parts[1:],
                                "description": (
                                    f"Run {name.strip()}"
                                ),
                                "suite": name.strip(),
                            }
                    selector = (
                        ts.get("file")
                        or ts.get("selector")
                        or ts.get("path")
                        or ts.get("spec")
                    )
                    suite_cands.append(
                        {
                            "name": name.strip(),
                            "mechanism": ts.get(
                                "mechanism", "spec_file"
                            ),
                            "selector": selector,
                            "source": (
                                ts.get("source") or selector
                            ),
                            "command": cmd_obj,
                            "deterministic": bool(
                                ts.get(
                                    "deterministic",
                                    bool(cmd_obj),
                                )
                            ),
                            "confidence": float(
                                ts.get("confidence", 0.8)
                            ),
                            "metadata": {},
                        }
                    )
                if suite_cands:
                    out["suite_candidates"] = suite_cands

            if not out.get("execution_commands"):
                exec_cmds = []
                for ts in test_suites:
                    if not isinstance(ts, dict):
                        continue
                    name = ts.get("name", "")
                    npm_script_ec = ts.get("npmScript") or ts.get("npm_script")
                    cmd_str = (
                        ts.get("command")
                        or ts.get("run_command")
                        or ts.get("cmd")
                    )
                    if not cmd_str and npm_script_ec and isinstance(npm_script_ec, str):
                        cmd_str = f"npm run {npm_script_ec.strip()}"
                    if (
                        not isinstance(cmd_str, str)
                        or not cmd_str.strip()
                    ):
                        continue
                    try:
                        parts = shlex.split(cmd_str.strip())
                    except ValueError:
                        parts = cmd_str.strip().split()
                    if not parts:
                        continue
                    exec_cmds.append(
                        {
                            "executable": parts[0],
                            "arguments": parts[1:],
                            "description": f"Run {name}",
                            "suite": name or None,
                        }
                    )
                if exec_cmds:
                    out["execution_commands"] = exec_cmds

        # ---- selected_framework ----
        if not out.get("selected_framework"):
            fw_list = out.get("frameworks", [])
            if isinstance(fw_list, list) and fw_list:
                out["selected_framework"] = fw_list[0]

        # ---- selected_runner ----
        if not out.get("selected_runner"):
            rc = out.get("runner_candidates", [])
            if isinstance(rc, list) and rc:
                out["selected_runner"] = rc[0]

        return out

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
