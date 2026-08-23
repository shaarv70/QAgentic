import json
import shutil
import subprocess

from ai.models.llm_request import LLMRequest
from ai.models.llm_response import LLMResponse
from ai.profiles.agent_profile import AgentProfile
from ai.token.token_usage import TokenUsage
from providers.base_provider import BaseProvider
from ai.exceptions.ai_exception import AIRateLimitError


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
        # On Windows, npm installs a .cmd wrapper; shutil.which resolves it.
        exe = shutil.which("claude")

        if exe is None:
            raise RuntimeError(
                "claude CLI not found on PATH. "
                "Install it with: npm install -g @anthropic-ai/claude-code"
            )

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

        # The CLI runs within a Claude Code session whose context may override
        # some CLI-level prompt behavior. Embedding the system instruction in
        # stdin ensures it is explicitly provided to the model.
        combined_input = (
            f"<system>\n{request.system_prompt}\n</system>\n\n"
            f"{request.user_prompt}"
        )

        if profile.response_format == "json":
            combined_input += (
                "\n\nIMPORTANT: Your response must be a raw JSON object only. "
                "No markdown, no code fences, no explanation — just the JSON."
            )

        cmd = [
            claude,
            "--print",
            "--output-format",
            "json",
            "--model",
            profile.model,
        ]

        # Claude CLI supports --max-tokens. Only add it when a value is
        # explicitly configured so existing provider behavior is preserved.
        if profile.max_output_tokens:
            cmd.extend(
                [
                    "--max-tokens",
                    str(profile.max_output_tokens),
                ]
            )

        try:
            result = subprocess.run(
                cmd,
                input=combined_input,
                capture_output=True,
                encoding="utf-8",
                timeout=180,
            )

        except FileNotFoundError:
            raise RuntimeError(
                f"claude CLI executable not runnable: {claude}"
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "Claude CLI request timed out after 180 seconds."
            )

        stderr = (result.stderr or "").strip()

        if result.returncode != 0:

            # Preserve the existing stderr-based rate-limit detection.
            if self._is_rate_limit_error(stderr):
                raise AIRateLimitError(
                    "Claude CLI rate limit exceeded.",
                    retry_after=None,
                )

            # Some Claude CLI failures can still return structured JSON.
            # Inspect stdout before falling back to the generic CLI error.
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