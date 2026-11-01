import json
import os
import pathlib
import shutil
import subprocess
import tempfile

from ai.models.llm_request import LLMRequest
from ai.models.llm_response import LLMResponse
from ai.profiles.agent_profile import AgentProfile
from ai.token.token_usage import TokenUsage
from providers.base_provider import BaseProvider
from ai.exceptions.ai_exception import AIRateLimitError
from utils.logger import logger


def _estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 characters per token, matching TokenManager."""
    if not text:
        return 0

    return max(1, len(text) // 4)


class ClaudeCLIProvider(BaseProvider):
    """
    Routes LLM calls through the Claude Code CLI
    (`claude --print`) instead of the Anthropic API directly.

    Authentication is handled by the configured Claude CLI environment.
    Requires `claude` to be available on PATH.
    """

    @staticmethod
    def _resolve_claude_executable() -> str:
        # On Windows, npm installs a .cmd wrapper (claude.CMD) that runs
        # through cmd.exe, which has an 8190-character command-line limit.
        # Long --system-prompt values exceed this limit even though the
        # Windows CreateProcess limit is 32767.
        # Fix: detect the .cmd wrapper and resolve the real claude.exe that
        # the batch file calls, then invoke it directly via CreateProcess.
        exe = shutil.which("claude")

        if exe is None:
            raise RuntimeError(
                "claude CLI not found on PATH. "
                "Install it with: npm install -g @anthropic-ai/claude-code"
            )

        if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
            candidate = (
                pathlib.Path(exe).parent
                / "node_modules"
                / "@anthropic-ai"
                / "claude-code"
                / "bin"
                / "claude.exe"
            )
            if candidate.exists():
                return str(candidate)

        return exe

    @staticmethod
    def _is_rate_limit_error(stderr: str) -> bool:
        """
        Determine whether Claude CLI stderr indicates a rate-limit condition.

        Exit codes alone are not reliable enough because Claude CLI does not
        expose a stable documented exit-code contract for rate limiting.
        """
        error = (stderr or "").lower()

        rate_limit_indicators = (
            "rate limit",
            "rate_limit",
            "ratelimit",
            "too many requests",
            "quota exceeded",
            "quota limit",
            "429",
        )

        return any(indicator in error for indicator in rate_limit_indicators)

    @staticmethod
    def _is_rate_limit_response(data: dict) -> bool:
        """
        Determine whether a structured Claude CLI JSON response represents
        a rate-limit condition.

        Claude CLI may expose the underlying API error status through
        `api_error_status`.
        """
        api_error_status = data.get("api_error_status")

        return str(api_error_status) == "429"

    def generate(
        self,
        request: LLMRequest,
        profile: AgentProfile,
    ) -> LLMResponse:

        if not isinstance(request, LLMRequest):
            raise TypeError("request must be an instance of LLMRequest.")

        if not isinstance(profile, AgentProfile):
            raise TypeError("profile must be an instance of AgentProfile.")

        claude = self._resolve_claude_executable()

        # Pass the QAgentic system prompt via --system-prompt so it REPLACES
        # the Claude Code default system context (~26K tokens of tool
        # definitions, CLAUDE.md, memory files, git state, etc.).
        # This keeps each LLM call at ~600 tokens of system context instead
        # of 26 000+, dramatically reducing latency.
        #
        # --no-session-persistence skips loading prior session history.
        system_prompt = request.system_prompt

        # The JSON enforcement is placed in BOTH the system prompt and the
        # user message.  --system-prompt appends to Claude Code's ~26K-token
        # default context, so a system-only instruction can be overridden by
        # the model's default rich-markdown style.  Repeating the instruction
        # as the final line of the user turn (the last thing the model reads
        # before generating) is what actually enforces JSON output.
        json_enforce = (
            "\n\nIMPORTANT: Output only the JSON object defined above — "
            "no markdown, no headers, no code fences, no surrounding text. "
            "Use the exact keys specified in the schema. "
            "Populate every field with your actual analysis."
        )

        # RepositoryExecution is excluded from json_enforce because it may
        # not define a strict JSON schema and needs free-form output.
        _SKIP_JSON_ENFORCE = {"RepositoryExecution"}

        # Prepend a no-tool-use guard to every user message.
        # Placed in the user turn (stdin) rather than --system-prompt to avoid
        # hitting the Windows command-line length limit on long system prompts.
        _NO_TOOL_PREFIX = (
            "IMPORTANT: Do NOT use any tools, browsers, web search, "
            "computer use, Bash, or file operations. "
            "Generate your response from training knowledge only.\n\n"
        )
        user_input = _NO_TOOL_PREFIX + request.user_prompt
        if (
            profile.response_format == "json"
            and profile.agent_name not in _SKIP_JSON_ENFORCE
        ):
            system_prompt += json_enforce
            user_input += json_enforce

        cmd = [
            claude,
            "--print",
            "--output-format",
            "json",
            "--model",
            profile.model,
            "--system-prompt",
            system_prompt,
            "--no-session-persistence",
            # Disable all MCP servers (browser MCP, playwright MCP, etc.)
            # so the model cannot open a browser while generating text responses.
            "--strict-mcp-config",
            # Disallow computer-use tool (built-in browser/screenshot control).
            "--disallowedTools", "computer",
        ]

        try:
            # Run from a neutral temp directory so the Claude CLI does not
            # treat the QAgentic project root as its own workspace and load
            # all project files (CLAUDE.md, source code, memory) into the
            # model context — which inflates input tokens and biases output.
            result = subprocess.run(
                cmd,
                input=user_input,
                capture_output=True,
                encoding="utf-8",
                timeout=1200,
                cwd=tempfile.gettempdir(),
            )

        except FileNotFoundError:
            raise RuntimeError(
                f"claude CLI executable not runnable: {claude}"
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "Claude CLI request timed out after 1200 seconds."
            )

        stderr = (result.stderr or "").strip()

        if result.returncode != 0:

            # Preserve stderr-based rate-limit detection.
            if self._is_rate_limit_error(stderr):
                raise AIRateLimitError(
                    "Claude CLI rate limit exceeded.",
                    retry_after=None,
                )

            # Some Claude CLI failures can still return structured JSON.
            try:
                error_data = json.loads(result.stdout or "")
            except json.JSONDecodeError:
                error_data = {}

            if self._is_rate_limit_response(error_data):
                raise AIRateLimitError(
                    "Claude CLI rate limit exceeded.",
                    retry_after=None,
                )

            raise RuntimeError(
                f"Claude CLI exited with code {result.returncode}: {stderr}"
            )

        try:
            data = json.loads(result.stdout)

        except json.JSONDecodeError:
            raise RuntimeError(
                f"Claude CLI returned non-JSON output: {result.stdout[:200]}"
            )

        # Handle a structured rate-limit response even when the CLI returns
        # a zero exit code.
        if self._is_rate_limit_response(data):
            raise AIRateLimitError(
                "Claude CLI rate limit exceeded.",
                retry_after=None,
            )

        content = data.get("result", "").strip()

        if not content:
            raise RuntimeError(
                "Claude CLI returned an empty result."
            )

        # Strip markdown code fences the CLI session sometimes adds
        # (for example: ```json ... ```)
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]

            if content.endswith("```"):
                content = content.rsplit(
                    "```",
                    1
                )[0].strip()

        # Prefer actual usage information when the Claude CLI provides it.
        # Fall back to the existing approximation when usage is unavailable.
        usage = data.get("usage") or {}

        actual_input_tokens = usage.get("input_tokens")
        actual_output_tokens = usage.get("output_tokens")
        actual_cache_creation_tokens = usage.get(
            "cache_creation_input_tokens"
        )
        actual_cache_read_tokens = usage.get(
            "cache_read_input_tokens"
        )

        logger.info(
         "Claude usage | input=%s | output=%s | cache_creation=%s | cache_read=%s",
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            usage.get("cache_creation_input_tokens", 0),
            usage.get("cache_read_input_tokens", 0),
        )
        if actual_input_tokens is not None:
            input_tokens = int(actual_input_tokens)

        else:
            input_tokens = (
                _estimate_tokens(request.system_prompt)
                + _estimate_tokens(request.user_prompt)
            )

        if actual_output_tokens is not None:
            output_tokens = int(actual_output_tokens)

        else:
            output_tokens = _estimate_tokens(content)

        cache_creation_input_tokens = int(
            actual_cache_creation_tokens or 0
        )

        cache_read_input_tokens = int(
            actual_cache_read_tokens or 0
        )

        token_usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
        )

        return LLMResponse(
            content=content,
            provider="ClaudeCLI",
            model=profile.model,
            token_usage=token_usage,
        )