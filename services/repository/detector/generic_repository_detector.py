from pathlib import Path

from domain.repository.repository_detector import RepositoryDetector
from domain.repository.repository_info import RepositoryInfo
from models.repository_execution_profile import SuiteCandidate


class GenericRepositoryDetector(RepositoryDetector):
    """
    Detects repository facts that do not belong to a specific
    framework or build technology.
    """

    _TEST_DIRECTORIES = (
        "test",
        "tests",
        "src/test",
        "src/tests",
        "e2e",
        "spec",
        "__tests__",
    )

    _CONFIGURATION_FILES = (
        "package.json",
        "pyproject.toml",
        "pytest.ini",
        "setup.py",
        "setup.cfg",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
    )

    _PROJECT_MARKERS = {
        "package.json": "node",
        "requirements.txt": "python",
        "pyproject.toml": "python",
        "setup.py": "python",
        "setup.cfg": "python",
        "pom.xml": "java",
        "build.gradle": "gradle",
        "build.gradle.kts": "gradle",
    }

    @property
    def name(self) -> str:
        return "generic_repository"

    def detect(
        self,
        repository_path: str,
        repository_info: RepositoryInfo,
    ) -> None:

        repository = Path(repository_path)

        self._detect_project_markers(
            repository,
            repository_info,
        )

        self._detect_test_locations(
            repository,
            repository_info,
        )

        self._detect_configuration_files(
            repository,
            repository_info,
        )

        self._detect_common_execution_scripts(
            repository,
            repository_info,
        )

    def _detect_project_markers(
        self,
        repository: Path,
        repository_info: RepositoryInfo,
    ) -> None:

        for marker, project_type in self._PROJECT_MARKERS.items():

            if (repository / marker).is_file():
                repository_info.add_project_type(
                    project_type
                )

    def _detect_test_locations(
        self,
        repository: Path,
        repository_info: RepositoryInfo,
    ) -> None:

        for directory in self._TEST_DIRECTORIES:

            if (repository / directory).is_dir():
                repository_info.add_test_location(
                    directory
                )

    def _detect_configuration_files(
        self,
        repository: Path,
        repository_info: RepositoryInfo,
    ) -> None:

        for filename in self._CONFIGURATION_FILES:

            path = repository / filename

            if path.is_file():
                repository_info.add_configuration_file(
                    filename
                )

    def _detect_common_execution_scripts(
        self,
        repository: Path,
        repository_info: RepositoryInfo,
    ) -> None:

        candidates = (
            "Makefile",
            "justfile",
            "Taskfile.yml",
            "Taskfile.yaml",
            "tox.ini",
        )

        for filename in candidates:

            if (repository / filename).is_file():

                repository_info.add_runner_candidate(
                    filename
                )