
import asyncio

from bootstrap.application_container import ApplicationContainer


async def main() -> None:
    container = ApplicationContainer()
    container.create_supervisor()
    executor = container.mcp_tool_executor

    server_name = "selenium"
    session_id = None

    print("\n=== Selenium MCP E2E Test ===")

    try:
        # ---------------------------------------------------------
        # 1. Discover Selenium MCP tools
        # ---------------------------------------------------------
        print("\n=== 1. Discover Selenium Tools ===")

        tools = await executor.discover_server_tools(server_name)

        print(f"Discovered {len(tools)} Selenium tools")

        if not tools:
            raise RuntimeError("No Selenium MCP tools were discovered.")

        required_tools = {
            "open_browser",
            "close_browser",
            "open_url",
            "wait_for_page",
            "get_page_title",
            "get_page_text",
        }

        discovered_names = {tool.name for tool in tools}

        missing_tools = required_tools - discovered_names

        if missing_tools:
            raise RuntimeError(
                f"Required Selenium tools are missing: {sorted(missing_tools)}"
            )

        print("Required tools verified")

        # ---------------------------------------------------------
        # 2. Open browser
        # ---------------------------------------------------------
        print("\n=== 2. Execute open_browser ===")

        result = await executor.execute(
            server_name=server_name,
            tool_name="open_browser",
            arguments={
                "browser": "chrome",
                "headless": False,
            },
        )

        if not result.success:
            raise RuntimeError(
                f"open_browser failed: {result.data}"
            )

        print("open_browser: SUCCESS")
        print(f"Data: {result.data}")

        if not isinstance(result.data, dict):
            raise RuntimeError(
                f"Expected dictionary from open_browser, "
                f"got {type(result.data)}"
            )

        session_id = result.data.get("session_id")

        if not session_id:
            raise RuntimeError(
                "open_browser succeeded but did not return session_id."
            )

        print(f"Browser session ID: {session_id}")

        # ---------------------------------------------------------
        # 3. Open URL
        # ---------------------------------------------------------
        print("\n=== 3. Execute open_url ===")

        result = await executor.execute(
            server_name=server_name,
            tool_name="open_url",
            arguments={
                "session_id": session_id,
                "url": "https://example.com",
            },
        )

        if not result.success:
            raise RuntimeError(
                f"open_url failed: {result.data}"
            )

        print("open_url: SUCCESS")
        print(f"Data: {result.data}")

        # ---------------------------------------------------------
        # 4. Wait for page
        # ---------------------------------------------------------
        print("\n=== 4. Execute wait_for_page ===")

        result = await executor.execute(
            server_name=server_name,
            tool_name="wait_for_page",
            arguments={
                "session_id": session_id,
            },
        )

        if not result.success:
            raise RuntimeError(
                f"wait_for_page failed: {result.data}"
            )

        print("wait_for_page: SUCCESS")
        print(f"Data: {result.data}")

        # ---------------------------------------------------------
        # 5. Get page title
        # ---------------------------------------------------------
        print("\n=== 5. Execute get_page_title ===")

        result = await executor.execute(
            server_name=server_name,
            tool_name="get_page_title",
            arguments={
                "session_id": session_id,
            },
        )

        if not result.success:
            raise RuntimeError(
                f"get_page_title failed: {result.data}"
            )

        print("get_page_title: SUCCESS")
        print(f"Data: {result.data}")

        # ---------------------------------------------------------
        # 6. Get page text
        # ---------------------------------------------------------
        print("\n=== 6. Execute get_page_text ===")

        result = await executor.execute(
            server_name=server_name,
            tool_name="get_page_text",
            arguments={
                "session_id": session_id,
            },
        )

        if not result.success:
            raise RuntimeError(
                f"get_page_text failed: {result.data}"
            )

        print("get_page_text: SUCCESS")

        text = result.data

        if isinstance(text, dict):
            print(f"Data: {text}")
        else:
            print(f"Data preview: {str(text)[:500]}")

        # ---------------------------------------------------------
        # 7. Close browser
        # ---------------------------------------------------------
        print("\n=== 7. Execute close_browser ===")

        result = await executor.execute(
            server_name=server_name,
            tool_name="close_browser",
            arguments={
                "session_id": session_id,
            },
        )

        if not result.success:
            raise RuntimeError(
                f"close_browser failed: {result.data}"
            )

        print("close_browser: SUCCESS")
        print(f"Data: {result.data}")

        session_id = None

        # ---------------------------------------------------------
        # Final result
        # ---------------------------------------------------------
        print("\n======================================")
        print("=== Selenium MCP E2E TEST PASSED ===")
        print("======================================")

    finally:
        # ---------------------------------------------------------
        # Safety cleanup
        # ---------------------------------------------------------
        #
        # If a failure occurs after open_browser, attempt to close
        # the browser so that ChromeDriver does not remain running.
        #
        if session_id:
            print("\nAttempting browser cleanup...")

            try:
                await executor.execute(
                    server_name=server_name,
                    tool_name="close_browser",
                    arguments={
                        "session_id": session_id,
                    },
                )

                print("Browser cleanup completed.")

            except Exception as cleanup_error:
                print(
                    f"Browser cleanup failed: {cleanup_error}"
                )


if __name__ == "__main__":
    asyncio.run(main())

