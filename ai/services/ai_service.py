import json
import time
from ai.exceptions.ai_exception import AIRateLimitError
from ai.services.pricing_service import PricingService
from ai.token.token_manager import TokenManager
from ai.models.llm_request import LLMRequest
from ai.models.llm_response import LLMResponse
from registries.agent_profile_registry import AgentProfileRegistry
from config import LLM_PROVIDER
from registries.provider_registry import ProviderRegistry
from utils.logger import logger


class AIService:

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        profile_registry: AgentProfileRegistry,
        token_manager: TokenManager,
        pricing_service: PricingService,
    ):
        self.provider_registry = provider_registry
        self.profile_registry = profile_registry
        self.token_manager = token_manager
        self.pricing_service = pricing_service



    def generate(self,agent_name: str,request: LLMRequest,) -> LLMResponse:

        profile = self.profile_registry.get(agent_name)

        input_tokens = self.token_manager.estimate_prompt_tokens(
            request.system_prompt,
            request.user_prompt,
        )

        logger.info("LLM request | agent=%s | estimated_input_tokens=%d",agent_name,input_tokens,)

        provider = self.provider_registry.get(LLM_PROVIDER)

        response = self._generate_with_retry(provider=provider,request=request,profile=profile,)

        if response.token_usage:
            usage = response.token_usage

            response.cost = self.pricing_service.calculate(
                model=response.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_creation_input_tokens=(usage.cache_creation_input_tokens),
                cache_read_input_tokens=(usage.cache_read_input_tokens),)

            logger.info(
                "LLM cost | agent=%s | model=%s | "
                "input_cost=$%.8f | output_cost=$%.8f | total_cost=$%.8f",
                agent_name,
                response.model,
                response.cost.input_cost,
                response.cost.output_cost,
                response.cost.total_cost,
            )

        return response



    def generate_json(self,agent_name: str,request: LLMRequest,) -> dict:

        response = self.generate(agent_name,request,)

        content = response.content.strip()

        logger.info(
            "generate_json raw content | agent=%s | length=%d | preview=%r",
            agent_name,
            len(content),
            content[:800],
        )

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        import re as _re
        decoder = json.JSONDecoder()

        # The LLM often wraps its final answer in a ```json ... ``` fence after
        # reasoning text.  Use the LAST fence — earlier fences may be examples
        # or evidence echoes embedded in the reasoning.
        fence_matches = list(_re.finditer(
            r'```(?:json)?\s*\n?([\s\S]*?)\n?```',
            content,
        ))
        for fence in reversed(fence_matches):
            try:
                candidate = fence.group(1).strip()
                obj, _ = decoder.raw_decode(candidate)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass

        # No code fence worked — scan every '{' for a valid JSON object and
        # pick the one most likely to be the analysis result:
        # prefer dicts that have recognised analysis output keys, then fall
        # back to the largest dict by serialised length.
        dict_candidates = []
        for match in _re.finditer(r'\{', content):
            try:
                obj, _ = decoder.raw_decode(content, match.start())
                if isinstance(obj, dict):
                    dict_candidates.append(obj)
            except json.JSONDecodeError:
                pass

        if dict_candidates:
            _ANALYSIS_KEYS = {
                "frameworks", "project_types", "test_locations",
                "execution_commands", "selected_framework", "runner_candidates",
            }
            analysis_dicts = [
                d for d in dict_candidates if _ANALYSIS_KEYS & d.keys()
            ]
            if analysis_dicts:
                return max(analysis_dicts, key=lambda d: len(_ANALYSIS_KEYS & d.keys()))
            return max(dict_candidates, key=lambda d: len(json.dumps(d)))

        # Last resort: the LLM may have returned structurally complete JSON
        # that is merely missing closing brackets (truncated response).
        # Walk the content character-by-character, track bracket depth, and
        # append whatever closing tokens are needed.
        repaired = self._repair_truncated_json(content)
        if repaired is not None:
            logger.warning(
                "generate_json repaired truncated JSON | agent=%s", agent_name
            )
            return repaired

        raise ValueError(
            f"Invalid JSON returned by LLM:\n{content}"
        )

    @staticmethod
    def _repair_truncated_json(content: str) -> dict | None:
        """Append missing closing brackets to a truncated JSON object."""
        stack: list[str] = []
        in_string = False
        escape = False
        for ch in content:
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                stack.append("}")
            elif ch == "[":
                stack.append("]")
            elif ch in ("}", "]") and stack and stack[-1] == ch:
                stack.pop()
        if not stack:
            return None  # already balanced — nothing to repair
        repaired = content + "".join(reversed(stack))
        try:
            obj = json.loads(repaired)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None




    def _generate_with_retry(self,provider,request: LLMRequest,profile,) -> LLMResponse:

        max_attempts = 3

        for attempt in range(max_attempts):

            try:
                return provider.generate(
                    request=request,
                    profile=profile,
                )

            except AIRateLimitError as ex:

                if attempt == max_attempts - 1:
                    raise

                delay = ex.retry_after

                if delay is None:
                    delay = 2 ** attempt

                logger.warning(
                    "LLM rate limit | "
                    "attempt=%d/%d | retry_in=%.2fs",
                    attempt + 1,
                    max_attempts,
                    delay,
                )

                time.sleep(delay)

        raise RuntimeError(
            "LLM generation failed after retry attempts.")