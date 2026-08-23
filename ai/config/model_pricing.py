from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """
    Pricing for a model.

    Prices are expressed as USD per 1 million tokens.

    Cache pricing defaults to zero so providers/models that do not expose
    cache-specific usage continue to use the existing input/output pricing.
    """

    input_per_million: float
    output_per_million: float
    cache_creation_per_million: float = 0.0
    cache_read_per_million: float = 0.0

    def calculate(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_creation_input_tokens: int = 0,
        cache_read_input_tokens: int = 0,
    ) -> tuple[float, float, float]:
        """
        Calculate input, output and total cost.

        Cache creation and cache read costs are included in the aggregate
        input cost. The three-value return shape is preserved so existing
        PricingService callers remain compatible.
        """

        input_cost = (
            input_tokens / 1_000_000
        ) * self.input_per_million

        cache_creation_cost = (
            cache_creation_input_tokens / 1_000_000
        ) * self.cache_creation_per_million

        cache_read_cost = (
            cache_read_input_tokens / 1_000_000
        ) * self.cache_read_per_million

        output_cost = (
            output_tokens / 1_000_000
        ) * self.output_per_million

        total_input_cost = (
            input_cost
            + cache_creation_cost
            + cache_read_cost
        )

        total_cost = total_input_cost + output_cost

        return total_input_cost, output_cost, total_cost