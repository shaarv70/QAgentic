from abc import ABC, abstractmethod


class CredentialProvider(ABC):
    """
    Resolves credentials required by external MCP servers.

    Implementations may obtain credentials from environment
    variables, OAuth flows, secret managers, CI/CD systems, etc.
    """

    @abstractmethod
    def get_headers(self, server_name: str) -> dict[str, str]:
        """
        Return authentication headers for the requested MCP server.
        """
        raise NotImplementedError