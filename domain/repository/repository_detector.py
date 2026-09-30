from abc import ABC, abstractmethod

from domain.repository.repository_info import RepositoryInfo


class RepositoryDetector(ABC):
    """
    Extension point for deterministic repository discovery.

    A detector inspects a repository and enriches RepositoryInfo.

    Detectors:
        - must not execute tests
        - must not modify the repository
        - must not invoke an LLM
        - should only add deterministic discovery information
    """

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def detect(
        self,
        repository_path: str,
        repository_info: RepositoryInfo,
    ) -> None:
        raise NotImplementedError