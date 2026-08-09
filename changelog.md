# Changelog

All notable changes to QAgentic are documented in this file.

The project follows semantic versioning where practical.

---

## [0.4.0] - 2026-08-09

### Added

#### AI Infrastructure

* Introduced centralized `AIService` for LLM interaction.
* Introduced standardized `LLMRequest`.
* Introduced standardized `LLMResponse`.
* Introduced `AgentProfile` for agent-specific model configuration.
* Introduced `AgentProfileRegistry`.
* Introduced provider abstraction through `BaseProvider`.
* Standardized provider execution around:

  ```python
  generate(
      request: LLMRequest,
      profile: AgentProfile
  ) -> LLMResponse
  ```

#### Prompt & Context Architecture

* Introduced centralized `PromptBuilder`.
* Introduced centralized `ContextBuilder`.
* Separated runtime context preparation from prompt construction.
* Standardized system-prompt and user-prompt generation across generators.
* Updated review and correction prompt flows to use the new context architecture.

#### Token & Cost Management

* Added actual provider token usage tracking.
* Added `TokenUsage`.
* Added model pricing configuration.
* Added `PricingService`.
* Added `LLMCost`.
* Added centralized request cost calculation.
* Added LLM cost logging per agent/request.

#### Providers

* Updated Groq to the standardized LLM request/response contract.
* Updated Ollama to the standardized LLM request/response contract.
* Provider implementations now receive model and temperature through `AgentProfile`.
* Provider-specific response handling is converted into the common `LLMResponse` model.

### Changed

* Reworked the generator/agent interaction around the centralized AI infrastructure.
* Moved LLM interaction away from the legacy direct LLM service path.
* Standardized provider-independent response handling.
* Centralized token and cost accounting.
* Improved separation of concerns between:

  * Agents
  * Generators
  * Prompt builders
  * Context builders
  * AI service
  * Providers
* Removed the legacy `LLMService` path from the active architecture.
* Removed obsolete prompt implementations that were replaced by the current prompt-builder architecture.

### Architecture

The resulting v0.4 flow is:

```text
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
```

### Validation

* End-to-end workflow validated through the current Requirement → Planning → Execution → Review → Correction → Re-review → Automation flow.
* Token usage was observed from actual provider responses.
* LLM cost calculation was validated through runtime logs.
* Provider contract was standardized for the active Groq and Ollama implementations.

### Known Limitations

* Large review/correction contexts can exceed provider token limits.
* Context minimization and advanced context-management strategies are intentionally deferred.
* Automatic provider fallback is not part of v0.4.
* Advanced memory and retrieval capabilities are not part of v0.4.

---

## [0.3.0]

### Added

* LangGraph workflow orchestration.
* Workflow manager.
* Workflow nodes.
* Application container.
* Dependency-aware workflow execution.
* Parallel task execution.
* Artifact publishing.

### Added Workflow Capabilities

* Requirement processing.
* Planning.
* Execution.
* Review.
* Correction.
* Publishing.

---

## [0.2.0]

### Added

* Task planning.
* Dependency-aware execution.
* AI artifact review.
* Automatic correction.
* Parallel execution.
* Retry mechanisms.

---

## [0.1.0]

### Added

* Initial AI QA agent framework.
* Requirement processing.
* Initial QA artifact generation.
* Initial agent/service architecture.

---

[0.4.0]: https://github.com/shaarv70/QAgentic/releases/tag/v0.4.0
