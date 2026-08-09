from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LLMCost:
    """
    Represents the calculated cost of a single LLM request.

    Costs are represented in USD.
    """

    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0