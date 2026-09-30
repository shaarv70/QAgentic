import importlib
import json
from typing import Any, cast

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from mcp_integration.auth.credential_provider import CredentialProvider
from mcp_integration.client.models import MCPToolResult
from mcp_integration.config import MCPServerConfig


class MCPClient:
    """
    QAgentic abstraction over the MCP SDK client.

    Supports:
        - Streamable HTTP MCP servers
        - Stdio MCP servers

    Responsibilities:
        - Establish MCP connections
        - Initialize MCP sessions
        - Discover MCP tools
        - Invoke MCP tools
        - Close MCP resources cleanly

    Compatible with MCP SDK 2.1.x.
    """

    def __init__(
        self,
        config: MCPServerConfig,
        credential_provider: CredentialProvider,
    ):
        self.config = config
        self.credential_provider = credential_provider

        self._streamable_http_context = None
        self._stdio_context = None
        self._session_context = None

        self._session: ClientSession | None = None
        self._streams = None

        # Keep as Any to avoid Pylance issues around httpx2.
        self._http_client: Any = None

    async def connect(
        self,
        config: MCPServerConfig | None = None,
    ) -> None:
        """
        Connect to the configured MCP server.

        The optional config parameter is retained for compatibility
        with the current executor implementation.
        """

        if config is not None:
            self.config = config

        if not self.config.enabled:
            raise RuntimeError(
                f"MCP server '{self.config.name}' is disabled."
            )

        if self.config.transport == "streamable-http":
            await self._connect_streamable_http()
            return

        if self.config.transport == "stdio":
            await self._connect_stdio()
            return

        raise ValueError(
            f"Unsupported MCP transport: {self.config.transport}"
        )

    async def _connect_streamable_http(self) -> None:
        """
        Establish a Streamable HTTP MCP connection.

        Compatible with MCP SDK 2.1.x.

        MCP 2.1.x streamable_http_client() yields:

            read_stream
            write_stream

        There is NO third get_session_id value.
        """

        url = self.config.url

        if not isinstance(url, str) or not url:
            raise ValueError(
                f"MCP server '{self.config.name}' "
                "does not have a valid URL configured."
            )

        configured_headers = dict(self.config.headers or {})

        credential_headers = self.credential_provider.get_headers(
            self.config.name
        )

        headers = {
            **configured_headers,
            **credential_headers,
        }

        # MCP 2.x uses httpx2.
        # Dynamic import avoids Pylance's:
        # "Import 'httpx2' could not be resolved"
        try:
            httpx2 = importlib.import_module("httpx2")
        except ImportError as exc:
            raise RuntimeError(
                "httpx2 is required by MCP 2.x but could not be imported. "
                "Verify that httpx2 is installed in the Python environment "
                "running the AI-QA-Agent."
            ) from exc

        self._http_client = httpx2.AsyncClient(
            headers=headers,
            follow_redirects=True,
        )

        # IMPORTANT:
        # This is the transport context.
        self._streamable_http_context = streamable_http_client(
            url,
            http_client=self._http_client,
        )

        try:
            # MCP 2.1.x returns EXACTLY TWO values.
            read_stream, write_stream = cast(tuple[Any, Any],await self._streamable_http_context.__aenter__(),)

            self._streams = (
                read_stream,
                write_stream,
            )

            # ClientSession itself is another async context manager.
            self._session_context = ClientSession(
                read_stream,
                write_stream,
            )

            self._session = (
                await self._session_context.__aenter__()
            )

            await self._session.initialize()

        except Exception:
            await self._cleanup_streamable_http()
            raise

    async def _connect_stdio(self) -> None:
        """
        Establish an MCP connection over stdio.

        Retained for compatibility with MCP servers that use
        local process-based transport.
        """

        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        if not self.config.command:
            raise RuntimeError(
                f"MCP server '{self.config.name}' "
                "does not have a command configured."
            )

        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.environment or None,
        )

        self._stdio_context = stdio_client(
            server_params
        )

        try:
            read_stream, write_stream = (
                await self._stdio_context.__aenter__()
            )

            self._streams = (
                read_stream,
                write_stream,
            )

            self._session_context = ClientSession(
                read_stream,
                write_stream,
            )

            self._session = (
                await self._session_context.__aenter__()
            )

            await self._session.initialize()

        except Exception:
            await self._cleanup_stdio()
            raise

    async def list_tools(self) -> list[Any]:
        """
        Discover tools exposed by the connected MCP server.
        """

        if self._session is None:
            raise RuntimeError(
                "MCP client is not connected."
            )

        result = await self._session.list_tools()

        return result.tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """
        Invoke an MCP tool.
        """

        if self._session is None:
            raise RuntimeError(
                "MCP client is not connected."
            )

        return await self._session.call_tool(
            tool_name,
            arguments or {},
        )

    async def has_tool(
        self,
        tool_name: str,
    ) -> bool:
        """
        Check whether the connected MCP server
        exposes the requested tool.
        """

        tools = await self.list_tools()

        return any(
            tool.name == tool_name
            for tool in tools
        )

    async def call_required_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPToolResult:
        """
        Validate tool availability before invocation.
        """

        if not await self.has_tool(tool_name):
            raise RuntimeError(
                f"MCP tool '{tool_name}' is not available."
            )

        result = await self.call_tool(
            tool_name,
            arguments,
        )

        if getattr(result, "is_error", False):
            return MCPToolResult(
                success=False,
                error=str(result),
            )

        if not result.content:
            return MCPToolResult(
                success=True,
                data=None,
            )

        first_content = result.content[0]

        text = getattr(
            first_content,
            "text",
            None,
        )

        if text is None:
            return MCPToolResult(
                success=True,
                data=first_content,
            )

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = text

        return MCPToolResult(
            success=True,
            data=data,
        )

    async def _cleanup_streamable_http(self) -> None:
        """
        Best-effort cleanup for a failed Streamable HTTP connection.

        Resources are cleaned in reverse order.
        """

        # 1. Close ClientSession.
        if self._session_context is not None:
            try:
                await self._session_context.__aexit__(
                    None,
                    None,
                    None,
                )
            except BaseException:
                pass
            finally:
                self._session_context = None
                self._session = None

        # 2. Close Streamable HTTP transport.
        if self._streamable_http_context is not None:
            try:
                await self._streamable_http_context.__aexit__(
                    None,
                    None,
                    None,
                )
            except BaseException:
                pass
            finally:
                self._streamable_http_context = None

        self._streams = None

        # 3. Close HTTP client.
        if self._http_client is not None:
            try:
                await self._http_client.aclose()
            except BaseException:
                pass
            finally:
                self._http_client = None

    async def _cleanup_stdio(self) -> None:
        """
        Best-effort cleanup for a failed stdio connection.
        """

        # 1. Close ClientSession.
        if self._session_context is not None:
            try:
                await self._session_context.__aexit__(
                    None,
                    None,
                    None,
                )
            except BaseException:
                pass
            finally:
                self._session_context = None
                self._session = None

        # 2. Close stdio transport.
        if self._stdio_context is not None:
            try:
                await self._stdio_context.__aexit__(
                    None,
                    None,
                    None,
                )
            except BaseException:
                pass
            finally:
                self._stdio_context = None

        self._streams = None

    async def close(self) -> None:
        """
        Close the MCP session and transport cleanly.

        Closing order:

            1. MCP ClientSession
            2. Streamable HTTP transport
            3. stdio transport
            4. HTTP client
        """

        # 1. Close MCP ClientSession.
        if self._session_context is not None:
            try:
                await self._session_context.__aexit__(
                    None,
                    None,
                    None,
                )
            finally:
                self._session_context = None
                self._session = None

        # 2. Close Streamable HTTP transport.
        if self._streamable_http_context is not None:
            try:
                await self._streamable_http_context.__aexit__(
                    None,
                    None,
                    None,
                )
            finally:
                self._streamable_http_context = None
                self._streams = None

        # 3. Close stdio transport.
        if self._stdio_context is not None:
            try:
                await self._stdio_context.__aexit__(
                    None,
                    None,
                    None,
                )
            finally:
                self._stdio_context = None

        # 4. Close HTTP client.
        if self._http_client is not None:
            try:
                await self._http_client.aclose()
            finally:
                self._http_client = None

    async def __aenter__(self) -> "MCPClient":
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        await self.close()