from abc import ABC, abstractmethod
from typing import Any


class EnvironmentProvider(ABC):

    @abstractmethod
    async def execute_command(
        self,
        command: str,
        working_directory: str,
        timeout_seconds: int = 300,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def create_directory(
        self,
        path: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read_file(
        self,
        path: str,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def write_file(
        self,
        path: str,
        content: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_path(
        self,
        path: str,
    ) -> None:
        raise NotImplementedError