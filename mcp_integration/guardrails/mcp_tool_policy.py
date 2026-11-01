from enum import Enum


class MCPToolAccessLevel(str, Enum):

    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    UNKNOWN = "unknown"


class MCPToolPolicy:
    """
    Determines the QAgentic access classification for an MCP tool.

    Classification priority:
      1. Server-specific tool overrides  — explicit, highest priority
      2. MCP annotation (destructive_hint) — from the server's own metadata
      3. Keyword heuristics on tool name  — fallback

    Server overrides exist because some MCP servers set destructive_hint=True
    on tools that are only observational in QAgentic's context (e.g. Playwright's
    browser_navigate, which modifies browser state but never touches user data).
    """

    # Explicit access levels for known server + tool combinations.
    # These override both MCP annotations and keyword heuristics.
    _SERVER_TOOL_OVERRIDES: dict[tuple[str, str], "MCPToolAccessLevel"] = {
        # --- Playwright MCP ---
        # Navigation and observation tools are safe in page-inspection context.
        ("playwright", "browser_navigate"):           MCPToolAccessLevel.WRITE,
        ("playwright", "browser_snapshot"):           MCPToolAccessLevel.READ,
        ("playwright", "browser_take_screenshot"):    MCPToolAccessLevel.READ,
        ("playwright", "browser_screenshot"):         MCPToolAccessLevel.READ,
        ("playwright", "browser_click"):              MCPToolAccessLevel.WRITE,
        ("playwright", "browser_type"):               MCPToolAccessLevel.WRITE,
        ("playwright", "browser_fill"):               MCPToolAccessLevel.WRITE,
        ("playwright", "browser_select_option"):      MCPToolAccessLevel.WRITE,
        ("playwright", "browser_check"):              MCPToolAccessLevel.WRITE,
        ("playwright", "browser_uncheck"):            MCPToolAccessLevel.WRITE,
        ("playwright", "browser_hover"):              MCPToolAccessLevel.WRITE,
        ("playwright", "browser_press_key"):          MCPToolAccessLevel.WRITE,
        ("playwright", "browser_wait_for"):           MCPToolAccessLevel.READ,
        ("playwright", "browser_close"):              MCPToolAccessLevel.WRITE,
        ("playwright", "browser_tab_new"):            MCPToolAccessLevel.WRITE,
        ("playwright", "browser_tab_close"):          MCPToolAccessLevel.WRITE,
        ("playwright", "browser_tab_select"):         MCPToolAccessLevel.WRITE,
        ("playwright", "browser_tab_list"):           MCPToolAccessLevel.READ,
        ("playwright", "browser_network_requests"):   MCPToolAccessLevel.READ,
        ("playwright", "browser_console_messages"):   MCPToolAccessLevel.READ,
        ("playwright", "browser_evaluate"):           MCPToolAccessLevel.WRITE,
        ("playwright", "browser_resize"):             MCPToolAccessLevel.WRITE,
        ("playwright", "browser_handle_dialog"):      MCPToolAccessLevel.WRITE,
        ("playwright", "browser_file_upload"):        MCPToolAccessLevel.WRITE,
        ("playwright", "browser_pdf_save"):           MCPToolAccessLevel.WRITE,
        # --- GitHub MCP ---
        # Read operations stay READ even if keyword heuristics would say otherwise.
        ("github", "get_file_contents"):              MCPToolAccessLevel.READ,
        ("github", "list_commits"):                   MCPToolAccessLevel.READ,
        ("github", "search_repositories"):            MCPToolAccessLevel.READ,
        ("github", "search_code"):                    MCPToolAccessLevel.READ,
        ("github", "list_issues"):                    MCPToolAccessLevel.READ,
        ("github", "get_issue"):                      MCPToolAccessLevel.READ,
        ("github", "list_pull_requests"):             MCPToolAccessLevel.READ,
        ("github", "get_pull_request"):               MCPToolAccessLevel.READ,
        ("github", "list_branches"):                  MCPToolAccessLevel.READ,
        ("github", "get_commit"):                     MCPToolAccessLevel.READ,
        ("github", "search_users"):                   MCPToolAccessLevel.READ,
        ("github", "get_user"):                       MCPToolAccessLevel.READ,
        ("github", "list_notifications"):             MCPToolAccessLevel.READ,
        ("github", "delete_file"):                    MCPToolAccessLevel.DESTRUCTIVE,
        ("github", "delete_repository"):              MCPToolAccessLevel.DESTRUCTIVE,
    }

    def classify(
        self,
        tool_name: str,
        annotations: object | None,
        server_name: str = "",
    ) -> MCPToolAccessLevel:

        # 1. Server-specific override takes highest priority.
        override = self._SERVER_TOOL_OVERRIDES.get((server_name, tool_name))
        if override is not None:
            return override

        # 2. MCP annotation hint.
        if annotations is not None:
            destructive = getattr(annotations, "destructive_hint", None)
            if destructive is True:
                return MCPToolAccessLevel.DESTRUCTIVE

        # 3. Keyword heuristic on tool name.
        return self._classify_by_name(tool_name)

    def _classify_by_name(self, tool_name: str) -> MCPToolAccessLevel:

        name = tool_name.lower()

        destructive_keywords = (
            "delete",
            "remove",
            "destroy",
            "terminate",
            "revoke",
        )

        write_keywords = (
            "create",
            "update",
            "write",
            "push",
            "merge",
            "fork",
            "add",
            "edit",
            "modify",
            "request",
            "run",
        )

        if any(keyword in name for keyword in destructive_keywords):
            return MCPToolAccessLevel.DESTRUCTIVE

        if any(keyword in name for keyword in write_keywords):
            return MCPToolAccessLevel.WRITE

        return MCPToolAccessLevel.READ
