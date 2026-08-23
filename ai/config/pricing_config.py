from ai.config.model_pricing import ModelPricing


# Prices are USD per 1 million tokens (input / output).
#
# These values represent public model list pricing and are used only for
# informational cost estimation inside QAgentic.
#
# They do NOT represent United Airlines / MARS / AWS enterprise billing
# rates, which may differ based on the company's agreement.
#
# Verify these values when upgrading models — pricing can change frequently.

MODEL_PRICING: dict[str, ModelPricing] = {

    # --- Groq ---
    "openai/gpt-oss-120b": ModelPricing(
        input_per_million=0.15,
        output_per_million=0.60,
    ),

    "llama-3.3-70b-versatile": ModelPricing(
        input_per_million=0.59,
        output_per_million=0.79,
    ),

    "llama-3.1-8b-instant": ModelPricing(
        input_per_million=0.05,
        output_per_million=0.08,
    ),

    "mixtral-8x7b-32768": ModelPricing(
        input_per_million=0.24,
        output_per_million=0.24,
    ),

    # --- Ollama (local — no monetary cost) ---
    "llama3.2": ModelPricing(
        input_per_million=0.0,
        output_per_million=0.0,
    ),

    "llama3.1": ModelPricing(
        input_per_million=0.0,
        output_per_million=0.0,
    ),

    # --- Claude (via Claude Code CLI) ---
    "claude-sonnet-4-6": ModelPricing(
        input_per_million=3.00,
        output_per_million=15.00,
        cache_creation_per_million=3.75,
        cache_read_per_million=0.30,
    ),

    "claude-sonnet-4-5-20251001": ModelPricing(
        input_per_million=3.00,
        output_per_million=15.00,
        cache_creation_per_million=3.75,
        cache_read_per_million=0.30,
    ),

    "claude-3-5-sonnet-20241022": ModelPricing(
        input_per_million=3.00,
        output_per_million=15.00,
        cache_creation_per_million=3.75,
        cache_read_per_million=0.30,
    ),

    "claude-3-haiku-20240307": ModelPricing(
        input_per_million=0.25,
        output_per_million=1.25,
        cache_creation_per_million=0.30,
        cache_read_per_million=0.025,
    ),

    "claude-3-opus-20240229": ModelPricing(
        input_per_million=15.00,
        output_per_million=75.00,
        cache_creation_per_million=18.75,
        cache_read_per_million=1.50,
    ),
}