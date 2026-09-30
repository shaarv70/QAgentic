import os

from mcp_integration.auth.credential_provider import (CredentialProvider,)


class EnvironmentCredentialProvider(CredentialProvider):
    """
    Resolves MCP authentication credentials from environment variables.

    Authentication is optional at the client layer. If a server does not
    have a configured token, no authentication headers are returned.
    """



    def get_headers(self,server_name: str,) -> dict[str, str]:

        token_variable = (f"QAGENTIC_{server_name.upper()}_TOKEN")

        token = os.getenv(token_variable)

        if not token:
            return {}

        return {"Authorization": f"Bearer {token}",}