Changelog

All notable changes to QAgentic are documented in this file.

The project follows semantic versioning where practical.

[0.5.0] - 2026-08-20

Added

Knowledge & Memory

Introduced persistent memory using SQLite.

Introduced memory models for reusable execution knowledge.

Introduced episodic memory for relevant execution experiences and outcomes.

Introduced procedural memory for reusable QA and workflow knowledge.

Added memory policies for memory handling and retrieval.

Semantic Retrieval

Introduced embedding-based semantic retrieval.

Added embedding provider abstraction.

Added semantic similarity-based memory search.

Added relevance threshold filtering.

Added Top-K memory retrieval.

Added capability-aware memory queries.

Added retrieval result ranking.

RAG

Introduced Retrieval-Augmented Generation (RAG) support.

Added memory context construction.

Integrated retrieved memory context with the existing context and prompt architecture.

Enabled previously stored knowledge to be reused during subsequent AI executions.

Separated retrieved knowledge from the original user requirement and runtime workflow state.

AI Infrastructure

Extended the centralized AI infrastructure to support retrieved knowledge context.

Added provider-independent rate-limit handling.

Added retry and backoff handling for provider rate-limit responses.

Preserved provider abstraction while adding knowledge retrieval to the generation flow.

Changed

Extended the execution context architecture to include relevant retrieved memory.

Integrated memory retrieval into the existing prompt/context flow.

Improved reuse of procedural QA knowledge across executions.

Extended application initialization to wire memory, retrieval, embedding, and RAG services.

Maintained provider-independent LLM interaction while adding the knowledge layer.

Architecture

The resulting v0.5 flow extends the existing AI architecture with persistent knowledge retrieval:

Agent / Task
     ↓
Memory Query
     ↓
Memory Context Service
     ↓
Memory Manager
     ↓
Memory Retriever
     ↓
Embedding Provider
     ↓
Semantic Retrieval
     ↓
Relevance Filtering
     ↓
Top-K Memories
     ↓
Memory Context
     ↓
ContextBuilder / PromptBuilder
     ↓
AIService
     ↓
Provider
     ↓
LLM

Validation

Persistent memory storage was integrated into the application runtime.

Semantic retrieval was integrated with the memory layer.

Retrieved knowledge can be supplied as context during AI generation.

The v0.5 architecture preserves the existing workflow orchestration and provider abstraction.

Seeded memory knowledge is retained in the repository for fresh installations.

Known Limitations

External repository and document indexing are not part of v0.5.

MCP-based external tool execution is not part of v0.5.

Guardrails and human approval workflows are planned for v0.6.

Autonomous test execution and self-healing capabilities are planned for future releases.

Advanced external knowledge sources are planned for future versions.

[0.4.0] - 2026-08-09

Added

AI Infrastructure

Introduced centralized AIService for LLM interaction.

Introduced standardized LLMRequest.

Introduced standardized LLMResponse.

Introduced AgentProfile for agent-specific model configuration.

Introduced AgentProfileRegistry.

Introduced provider abstraction through BaseProvider.

Standardized provider execution around:

generate(
    request: LLMRequest,
    profile: AgentProfile
) -> LLMResponse

Prompt & Context Architecture

Introduced centralized PromptBuilder.

Introduced centralized ContextBuilder.

Separated runtime context preparation from prompt construction.

Standardized system-prompt and user-prompt generation across generators.

Updated review and correction prompt flows to use the new context architecture.

Token & Cost Management

Added actual provider token usage tracking.

Added TokenUsage.

Added model pricing configuration.

Added PricingService.

Added LLMCost.

Added centralized request cost calculation.

Added LLM cost logging per agent/request.

Providers

Updated Groq to the standardized LLM request/response contract.

Updated Ollama to the standardized LLM request/response contract.

Provider implementations now receive model and temperature through AgentProfile.

Provider-specific response handling is converted into the common LLMResponse model.

Changed

Reworked the generator/agent interaction around the centralized AI infrastructure.

Moved LLM interaction away from the legacy direct LLM service path.

Standardized provider-independent response handling.

Centralized token and cost accounting.

Improved separation of concerns between:

Agents

Generators

Prompt builders

Context builders

AI service

Providers

Removed the legacy LLMService path from the active architecture.

Removed obsolete prompt implementations that were replaced by the current prompt-builder architecture.

Architecture

The resulting v0.4 flow is:

Agent
  ↓
Generator / Service
  ↓
PromptBuilder
  ↓
ContextBuilder
  ↓
LLMRequest
  ↓
AIService
  ↓
ProviderRegistry
  ↓
Provider
  ↓
LLMResponse
  ├── TokenUsage
  └── LLMCost

Validation

End-to-end workflow validated through the current Requirement → Planning → Execution → Review → Correction → Re-review → Automation flow.

Token usage was observed from actual provider responses.

LLM cost calculation was validated through runtime logs.

Provider contract was standardized for the active Groq and Ollama implementations.

Known Limitations

Large review/correction contexts can exceed provider token limits.

Context minimization and advanced context-management strategies are intentionally deferred.

Automatic provider fallback is not part of v0.4.

Advanced memory and retrieval capabilities are not part of v0.4.

[0.3.0]

Added

LangGraph workflow orchestration.

Workflow manager.

Workflow nodes.

Application container.

Dependency-aware workflow execution.

Parallel task execution.

Artifact publishing.

Added Workflow Capabilities

Requirement processing.

Planning.

Execution.

Review.

Correction.

Publishing.

[0.2.0]

Added

Task planning.

Dependency-aware execution.

AI artifact review.

Automatic correction.

Parallel execution.

Retry mechanisms.

[0.1.0]

Added

Initial AI QA agent framework.

Requirement processing.

Initial QA artifact generation.

Initial agent/service architecture.