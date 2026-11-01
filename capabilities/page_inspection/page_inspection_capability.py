import asyncio
import contextlib
import io
import os
import re
from typing import Any

from capabilities.base_capability import BaseCapability
from capabilities.page_inspection.models import PageInspectionResult
from models.capability_result import CapabilityResult
from utils.logger import logger

_PLAYWRIGHT_SERVER = "playwright"
_TOOL_NAVIGATE = "browser_navigate"
_TOOL_SNAPSHOT = "browser_snapshot"

# Maximum characters kept from the DOM snapshot to avoid bloating downstream prompts.
_MAX_SNAPSHOT_CHARS = 12_000

# Total time budget for the full inspect cycle (navigate + snapshot).
# npx @playwright/mcp takes ~2-3s to start (pinned version, cached).
# Heavy JS sites need 30-60s for navigation. 120s gives comfortable margin.
_INSPECTION_TIMEOUT_SECONDS = 120

# Timeout for the HTTP fallback page fetch.
_HTTP_INSPECT_TIMEOUT_SECONDS = 30


# ---------------------------------------------------------------------------
# HTML structure extraction (used by the HTTP fallback strategy)
# ---------------------------------------------------------------------------

def _parse_attr(attrs_str: str, attr: str) -> str:
    """Return the value of a single HTML attribute from a raw attributes string."""
    m = re.search(
        rf'\b{re.escape(attr)}\s*=\s*(?:"([^"]*?)"|\'([^\']*?)\'|(\S+?)(?:[ \t>/]|$))',
        attrs_str,
        re.IGNORECASE,
    )
    return (m.group(1) or m.group(2) or m.group(3) or "").strip() if m else ""


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def _extract_page_structure(html: str) -> tuple[str, str]:
    """
    Return (title, snapshot) extracted from raw HTML.
    snapshot is a concise, LLM-readable listing of interactive elements —
    enough for accurate selector and test-case generation.
    """
    lines: list[str] = []

    # Title
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = _strip_tags(m.group(1)) if m else ""
    if title:
        lines.append(f"Page: {title}")

    # Strip <script> / <style> blocks so their text doesn't pollute results.
    clean = re.sub(
        r"<(script|style)[^>]*>.*?</(script|style)>",
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Headings
    for lvl in range(1, 5):
        for m in re.finditer(rf"<h{lvl}[^>]*>(.*?)</h{lvl}>", clean, re.IGNORECASE | re.DOTALL):
            text = _strip_tags(m.group(1))
            if text:
                lines.append(f"H{lvl}: {text}")

    # Forms
    for m in re.finditer(r"<form([^>]*)>", clean, re.IGNORECASE):
        a = m.group(1)
        action = _parse_attr(a, "action")
        method = (_parse_attr(a, "method") or "GET").upper()
        lines.append(f"Form [{method} {action or '—'}]")

    # Inputs (skip hidden)
    for m in re.finditer(r"<input([^>]*)>", clean, re.IGNORECASE):
        a = m.group(1)
        t = (_parse_attr(a, "type") or "text").lower()
        if t == "hidden":
            continue
        label = (
            _parse_attr(a, "aria-label")
            or _parse_attr(a, "placeholder")
            or _parse_attr(a, "name")
            or _parse_attr(a, "id")
        )
        lines.append(f"  input[{t}] {label}".rstrip())

    # Textareas
    for m in re.finditer(r"<textarea([^>]*)>", clean, re.IGNORECASE):
        a = m.group(1)
        label = (
            _parse_attr(a, "aria-label")
            or _parse_attr(a, "placeholder")
            or _parse_attr(a, "name")
            or _parse_attr(a, "id")
        )
        lines.append(f"  textarea {label}".rstrip())

    # Selects + first 5 options
    for m in re.finditer(r"<select([^>]*)>(.*?)</select>", clean, re.IGNORECASE | re.DOTALL):
        a, opts_html = m.group(1), m.group(2)
        label = _parse_attr(a, "aria-label") or _parse_attr(a, "name") or _parse_attr(a, "id")
        opts = [
            _strip_tags(o)
            for o in re.findall(r"<option[^>]*>(.*?)</option>", opts_html, re.IGNORECASE | re.DOTALL)
        ]
        opts_clean = [o for o in opts if o][:5]
        opts_str = f" [{', '.join(opts_clean)}]" if opts_clean else ""
        lines.append(f"  select {label}{opts_str}".rstrip())

    # Buttons
    for m in re.finditer(r"<button([^>]*)>(.*?)</button>", clean, re.IGNORECASE | re.DOTALL):
        a = m.group(1)
        text = _strip_tags(m.group(2))
        t = (_parse_attr(a, "type") or "button").lower()
        label = _parse_attr(a, "aria-label") or text or _parse_attr(a, "id")
        lines.append(f"  button[{t}] {label}".rstrip())

    # Labels (form field associations)
    for m in re.finditer(r"<label([^>]*)>(.*?)</label>", clean, re.IGNORECASE | re.DOTALL):
        a = m.group(1)
        text = _strip_tags(m.group(2))
        for_attr = _parse_attr(a, "for")
        if text and len(text) < 100:
            for_str = f'[for="{for_attr}"]' if for_attr else ""
            lines.append(f"  label{for_str}: {text}")

    # Navigation links (up to 15 meaningful hrefs)
    link_count = 0
    for m in re.finditer(r"<a([^>]*)>(.*?)</a>", clean, re.IGNORECASE | re.DOTALL):
        if link_count >= 15:
            break
        a = m.group(1)
        href = _parse_attr(a, "href")
        text = _strip_tags(m.group(2))
        label = _parse_attr(a, "aria-label") or text
        if label and href and not href.startswith(("javascript:", "mailto:")):
            lines.append(f"  link: {label} → {href}")
            link_count += 1

    return title, "\n".join(l for l in lines if l.strip())


class PageInspectionCapability(BaseCapability):
    """
    Navigates to a target URL using Playwright MCP and captures
    the live DOM accessibility tree as structured context for
    downstream TestCase and Automation agents.

    Graceful degradation: if Playwright MCP is not running or the
    page cannot be reached, the capability still returns PASSED with
    an empty snapshot so the pipeline can continue using LLM knowledge.
    """

    def __init__(self, mcp_tool_executor) -> None:
        super().__init__()
        self.mcp_tool_executor = mcp_tool_executor

    @property
    def name(self) -> str:
        return "page_inspection"

    @property
    def review_required(self) -> bool:
        # page_inspection degrades gracefully — an empty snapshot is a
        # valid outcome (heavy/slow sites, corporate firewall, etc.).
        # Blocking the pipeline on a missing DOM snapshot would prevent
        # testcase/automation from running at all.
        return False

    def execute(self, task: Any, context: Any = None) -> CapabilityResult:
        url = self._resolve_url(task)
        if not url:
            return CapabilityResult(
                status="FAILED",
                error="page_inspection requires a target URL in task context.",
                retryable=False,
            )

        logger.info("PageInspection started | url=%s", url)

        try:
            result = self._run_inspection(url)
        except Exception as exc:
            logger.warning(
                "PageInspection failed — graceful degradation | url=%s | error=%s",
                url,
                exc,
            )
            result = PageInspectionResult(url=url, error=str(exc))

        if result.has_content():
            logger.info(
                "PageInspection completed | url=%s | snapshot_chars=%d",
                url,
                len(result.dom_snapshot),
            )
        else:
            logger.warning(
                "PageInspection completed with empty snapshot (MCP unavailable or page error) | url=%s",
                url,
            )

        return CapabilityResult(
            status="PASSED",
            data=result.to_dict(),
            retryable=False,
        )

    def _run_inspection(self, url: str) -> PageInspectionResult:
        strategy = os.getenv("PAGE_INSPECTION_STRATEGY", "mcp").lower()

        if strategy != "http":
            # Try Playwright MCP first; fall through to HTTP on any failure.
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    result = asyncio.run(
                        asyncio.wait_for(
                            self._inspect_async(url),
                            timeout=_INSPECTION_TIMEOUT_SECONDS,
                        )
                    )
                if result.has_content():
                    return result
                logger.info(
                    "PageInspection MCP returned empty snapshot — trying HTTP fallback | url=%s",
                    url,
                )
            except Exception as exc:
                logger.warning(
                    "PageInspection MCP failed — trying HTTP fallback | url=%s | error=%s",
                    url,
                    exc,
                )

        return self._run_http_inspection(url)

    def _run_http_inspection(self, url: str) -> PageInspectionResult:
        """Fetch the page via HTTP and extract structural element information."""
        import requests as _requests  # already in requirements.txt

        logger.info("PageInspection HTTP fetch | url=%s", url)
        try:
            response = _requests.get(
                url,
                timeout=_HTTP_INSPECT_TIMEOUT_SECONDS,
                headers={"User-Agent": "Mozilla/5.0 (QAgentic PageInspector/1.0)"},
            )
            response.raise_for_status()
            html = response.text
        except Exception as exc:
            raise RuntimeError(f"HTTP page fetch failed: {exc}") from exc

        title, snapshot = _extract_page_structure(html)
        if len(snapshot) > _MAX_SNAPSHOT_CHARS:
            snapshot = snapshot[:_MAX_SNAPSHOT_CHARS] + "\n... [snapshot truncated]"

        if snapshot:
            logger.info(
                "PageInspection HTTP completed | url=%s | snapshot_chars=%d",
                url,
                len(snapshot),
            )
        else:
            logger.warning(
                "PageInspection HTTP: no elements extracted | url=%s", url
            )

        return PageInspectionResult(url=url, title=title, dom_snapshot=snapshot)

    async def _inspect_async(self, url: str) -> PageInspectionResult:
        # Run navigate + snapshot within a SINGLE MCP client session so
        # they share the same browser instance.  Separate execute() calls
        # each spawn a fresh subprocess (stdio transport) with a blank
        # browser — the navigation would be lost before the snapshot runs.
        raw_results = await self.mcp_tool_executor.execute_session(
            _PLAYWRIGHT_SERVER,
            [
                # waitUntil='domcontentloaded' fires once the HTML is parsed,
                # without waiting for images/scripts/fonts to finish loading.
                # This avoids an indefinite hang on heavy sites or behind proxies
                # that interfere with HTTP/2 resource requests.
                (_TOOL_NAVIGATE, {"url": url, "waitUntil": "domcontentloaded"}),
                (_TOOL_SNAPSHOT, {}),
            ],
        )

        logger.info("PageInspection: navigation + snapshot complete | url=%s", url)

        snapshot_raw = raw_results[1] if len(raw_results) > 1 else None
        snapshot_text = self._extract_text(snapshot_raw)
        if len(snapshot_text) > _MAX_SNAPSHOT_CHARS:
            snapshot_text = snapshot_text[:_MAX_SNAPSHOT_CHARS] + "\n... [snapshot truncated]"

        return PageInspectionResult(url=url, dom_snapshot=snapshot_text)

    @staticmethod
    def _extract_text(result) -> str:
        if result is None:
            return ""

        # MCPToolResult wrapper (from execute())
        data = getattr(result, "data", None)
        if data is not None:
            if isinstance(data, str):
                return data
            if isinstance(data, dict):
                return data.get("snapshot", "") or data.get("text", "") or str(data)
            return str(data)

        # Raw MCP SDK result (from execute_session() → client.call_tool())
        # result.content is a list of content blocks with a .text attribute
        content = getattr(result, "content", None)
        if content:
            texts = []
            for block in content:
                text = getattr(block, "text", None)
                if text:
                    texts.append(text)
            return "\n".join(texts)

        return str(result) if result else ""

    @staticmethod
    def _resolve_url(task: Any) -> str | None:
        task_context = getattr(task, "context", None)
        if not isinstance(task_context, dict):
            return None
        for key in ("target_url", "url", "app_url", "application_url", "base_url"):
            val = task_context.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return None
