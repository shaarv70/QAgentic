from domain.repository.repository_info import RepositoryInfo
from models.repository_execution_profile import (
    RepositoryExecutionProfile,
    SuiteCandidate,
)


class RepositoryExecutionProfileBuilder:
    """
    Builds a repository execution profile from discovered repository facts.

    This class is intentionally framework-agnostic.

    It does NOT:
        - identify TestNG/JUnit/Pytest/etc.
        - select a framework by priority
        - construct framework-specific commands
        - execute tests
        - invoke an LLM
        - contain build-tool-specific logic

    Framework-specific execution behavior belongs behind
    pluggable execution adapters/providers.
    """

    def build(
        self,
        repository_info: RepositoryInfo,
        working_directory: str | None = None,
    ) -> RepositoryExecutionProfile:

        if repository_info is None:
            raise ValueError(
                "Repository information cannot be None."
            )

        profile = RepositoryExecutionProfile(
            project_types=list(
                repository_info.project_types
            ),
            frameworks=list(
                repository_info.frameworks
            ),
            test_locations=list(
                repository_info.test_locations
            ),
            configuration_files=list(
                repository_info.configuration_files
            ),
            runner_candidates=list(
                repository_info.runner_candidates
            ),
            working_directory=working_directory,
        )

        for candidate in repository_info.suite_candidates:
            self.add_suite_candidate(
                profile,
                candidate,
            )

        return profile

    @staticmethod
    def add_suite_candidate(
        profile: RepositoryExecutionProfile,
        candidate: SuiteCandidate,
    ) -> None:

        if not candidate.name:
            raise ValueError(
                "Suite candidate name cannot be empty."
            )

        profile.add_suite_candidate(candidate)