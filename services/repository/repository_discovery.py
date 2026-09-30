from pathlib import Path

from domain.repository.repository_detector import RepositoryDetector
from domain.repository.repository_info import RepositoryInfo


class RepositoryDiscovery:
    """
    Coordinates deterministic repository discovery.

    RepositoryDiscovery itself is technology agnostic.

    Technology-specific discovery belongs to registered
    RepositoryDetector implementations.
    """

    def __init__(
        self,
        detectors: list[RepositoryDetector] | None = None,
    ) -> None:

        self._detectors = list(
            detectors or []
        )

    def discover(
        self,
        working_directory: str,
    ) -> RepositoryInfo:

        if not working_directory:
            raise ValueError(
                "Working directory cannot be empty."
            )

        repository = Path(
            working_directory
        ).resolve()

        if not repository.exists():
            raise FileNotFoundError(
                f"Repository path does not exist: {repository}"
            )

        if not repository.is_dir():
            raise NotADirectoryError(
                f"Repository path is not a directory: {repository}"
            )

        repository_info = RepositoryInfo()

        for detector in self._detectors:

            detector.detect(
                repository_path=str(repository),
                repository_info=repository_info,
            )

        return repository_info