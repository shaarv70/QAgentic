from dataclasses import dataclass, field
from typing import Any

from models.repository_execution_profile import SuiteCandidate


@dataclass(slots=True)
class RepositoryInfo:
    """
    Deterministic facts discovered from a repository.

    This model is intentionally framework and build-tool agnostic.
    """

    project_types: list[str] = field(
        default_factory=list
    )

    frameworks: list[str] = field(
        default_factory=list
    )

    test_locations: list[str] = field(
        default_factory=list
    )

    configuration_files: list[str] = field(
        default_factory=list
    )

    runner_candidates: list[str] = field(
        default_factory=list
    )

    suite_candidates: list[SuiteCandidate] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def add_project_type(
        self,
        value: str,
    ) -> None:
        self._append_unique(
            self.project_types,
            value,
        )

    def add_framework(
        self,
        value: str,
    ) -> None:
        self._append_unique(
            self.frameworks,
            value,
        )

    def add_test_location(
        self,
        value: str,
    ) -> None:
        self._append_unique(
            self.test_locations,
            value,
        )

    def add_configuration_file(
        self,
        value: str,
    ) -> None:
        self._append_unique(
            self.configuration_files,
            value,
        )

    def add_runner_candidate(
        self,
        value: str,
    ) -> None:
        self._append_unique(
            self.runner_candidates,
            value,
        )

    def add_suite_candidate(
        self,
        candidate: SuiteCandidate,
    ) -> None:

        for existing in self.suite_candidates:
            if (
                existing.name == candidate.name
                and existing.mechanism == candidate.mechanism
                and existing.selector == candidate.selector
                and existing.source == candidate.source
            ):
                return

        self.suite_candidates.append(candidate)

    @staticmethod
    def _append_unique(
        values: list[str],
        value: str,
    ) -> None:

        normalized = value.strip()

        if normalized and normalized not in values:
            values.append(normalized)