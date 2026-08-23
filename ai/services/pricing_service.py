from ai.config.llm_cost import LLMCost
from ai.config.model_pricing import ModelPricing
from ai.config.pricing_config import MODEL_PRICING


class PricingService:
    """
    Resolves pricing for the configured LLM model.

    Pricing remains outside AIService so the service does not
    contain model-specific pricing logic.
    """

    def __init__(self):
        self.pricing = MODEL_PRICING

    def calculate(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_input_tokens: int = 0,
        cache_read_input_tokens: int = 0,
    ) -> LLMCost:
        """
        Calculate cost using the pricing configured for the model.

        Cache creation and cache read tokens are optional so existing
        providers that do not expose cache-specific usage remain
        fully compatible.
        """

        pricing = self.pricing.get(model)

        if pricing is None:
            raise ValueError(
                f"No pricing configured for model: {model}"
            )

        input_cost, output_cost, total_cost = pricing.calculate(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
        )

        return LLMCost(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
        )