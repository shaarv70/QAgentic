from ai.config.model_pricing import ModelPricing


MODEL_PRICING: dict[str, ModelPricing] = {
    "openai/gpt-oss-120b": ModelPricing(
        input_per_million=0.15,
        output_per_million=0.60,
    ),
}