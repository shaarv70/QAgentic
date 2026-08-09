import logging

"""
==========================================================
Token Manager
==========================================================

Purpose:
    Centralizes token counting and token usage tracking.

Why:
    LLM usage is measured in tokens rather than characters.
    We need this information before implementing prompt
    optimization or cost controls.

Current responsibility:
    - Estimate input token count
    - Record actual provider usage when available

Future responsibility:
    - Cost calculation
    - Token budgets
    - Per-agent usage statistics
    - Prompt optimization decisions
==========================================================
"""
logger = logging.getLogger(__name__)




class TokenManager:

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text.

        This is intentionally an estimate for now. We will
        introduce model-specific tokenization later because
        different models can tokenize the same text differently.
        """

        if not text:
            return 0

        # Rough estimate:
        # English text commonly averages around 4 characters
        # per token. This is NOT an exact tokenizer.
        return max(1, len(text) // 4)


    def estimate_prompt_tokens(self,system_prompt: str,user_prompt: str,) -> int:
        """
        Estimate total input tokens for an LLM request.
        """

        return (
            self.estimate_tokens(system_prompt)
            + self.estimate_tokens(user_prompt)
        )