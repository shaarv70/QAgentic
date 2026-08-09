from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """
    Pricing for a model.

    Prices are expressed as USD per 1 million tokens.
    """

    input_per_million: float
    output_per_million: float

    def calculate(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> tuple[float, float, float]:
        """
        Calculate input, output and total cost.
        """

        input_cost = (
            input_tokens / 1_000_000
        ) * self.input_per_million

        output_cost = (
            output_tokens / 1_000_000
        ) * self.output_per_million

        total_cost = input_cost + output_cost

        return input_cost, output_cost, total_cost