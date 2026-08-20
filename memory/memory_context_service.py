from ai.builders.context_builder import ContextBuilder
from constants.agent_names import AgentNames
from memory.models.memory_category import MemoryCategory
from memory.models.memory_query import MemoryQuery


class MemoryContextService:

    def __init__(
        self,
        context_builder: ContextBuilder,
    ) -> None:
        self.context_builder = context_builder



    def build(self,
        agent_name: str,
        query_text: str,
        capability: str | None = None,) -> str:

        enriched_query = self._build_query_text(query_text,capability,)

        policy = self._policy(agent_name)

        contexts = []

        if policy["semantic"] > 0:
            contexts.append(
                self._retrieve(
                    enriched_query,
                    MemoryCategory.SEMANTIC,
                    policy["semantic"],
                    capability,
                )
            )

        if policy["episodic"] > 0:
            contexts.append(
                self._retrieve(
                    enriched_query,
                    MemoryCategory.EPISODIC,
                    policy["episodic"],
                    capability,
                )
            )

        if policy["procedural"] > 0:
            contexts.append(
                self._retrieve(
                    enriched_query,
                    MemoryCategory.PROCEDURAL,
                    policy["procedural"],
                    capability,
                )
            )

        return "\n".join(
            context
            for context in contexts
            if context
        )

    def _retrieve(
        self,
        query_text: str,
        category: MemoryCategory,
        limit: int,
        capability: str | None = None,
    ) -> str:

        memory_context = (
            self.context_builder.build_memory_context(
                MemoryQuery(
                    query=query_text,
                    category=category,
                    capability=capability,
                    minimum_confidence=0.7,
                    limit=limit,
                )
            )
        )

        return self.context_builder.memory(
            memory_context
        )

    @staticmethod
    def _build_query_text(
        query_text: str,
        capability: str | None,
    ) -> str:

        if not capability:
            return query_text

        return (
            f"{query_text} "
            f"Capability: {capability}"
        )

    @staticmethod
    def _policy(agent_name: str) -> dict:

        policies = {

        AgentNames.REQUIREMENT_INTELLIGENCE: {
            "semantic": 1,
            "episodic": 0,
            "procedural": 1,
        },

        AgentNames.PLANNER: {
            "semantic": 1,
            "episodic": 0,
            "procedural": 1,
        },

        AgentNames.REVIEW: {
            "semantic": 0,
            "episodic": 1,
            "procedural": 1,
        },

        AgentNames.CORRECTION: {
            "semantic": 1,
            "episodic": 1,
            "procedural": 1,
        },

        AgentNames.TESTCASE: {
            "semantic": 1,
            "episodic": 1,
            "procedural": 1,
        },

        AgentNames.AUTOMATION: {
            "semantic": 1,
            "episodic": 1,
            "procedural": 1,
        },

        AgentNames.DATABASE: {
            "semantic": 1,
            "episodic": 1,
            "procedural": 1,
        },

        AgentNames.SUMMARY: {
            "semantic": 1,
            "episodic": 0,
            "procedural": 1,
        },
    }

        return policies.get(
        agent_name,
        {
            "semantic": 1,
            "episodic": 0,
            "procedural": 1,
        },
    )