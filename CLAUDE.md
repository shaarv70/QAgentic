# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the application:**
```bash
python app.py
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Setup MARS Gateway (UAL enterprise, one-time):**
```bash
python setup_claude_code_mars_oidc.py
```

There are no automated tests in this codebase yet.

## Configuration

Copy `.env.example` to `.env` and set at least `LLM_PROVIDER` and the corresponding API key or connection details.

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | Active provider: `groq`, `ollama`, or `claude_cli` |
| `MODEL_NAME` | Optional override applied to all agent profiles; if unset, each provider uses its default |
| `GROQ_API_KEY` | Required when `LLM_PROVIDER=groq` |
| `OLLAMA_URL` | Required when `LLM_PROVIDER=ollama` |
| `OUTPUT_FOLDER` | Directory for generated artifacts (default: `generated`) |

The `claude_cli` provider authenticates through the company-provided Claude CLI / MARS environment. Run `setup_claude_code_mars_oidc.py` once to configure the company environment before using the Claude CLI provider.

QAgentic does not call the Anthropic API directly for the `claude_cli` provider. Claude requests are routed through the locally available Claude Code CLI.

## Architecture

### Entry Point and Wiring

`app.py` is the interactive loop. It creates an `ApplicationContainer` (`bootstrap/application_container.py`) which performs all dependency injection and returns a fully-wired `SupervisorAgent`. The container is the only place that instantiates and connects framework components — nothing else creates dependencies directly.

### End-to-End Execution Flow

```text
User requirement → SupervisorAgent → WorkflowManager → LangGraphEngine
  → Compiled LangGraph graph → Workflow nodes → Agents → Services/Generators
  → PromptBuilder → ContextBuilder + MemoryContextService → AIService
  → ProviderRegistry (selects provider) → LLMResponse
```

If the `RequirementIntelligenceAgent` returns `NEEDS_CLARIFICATION`, the `SupervisorAgent` prompts the user, updates the `WorkflowState`, and re-executes the full workflow until the requirement is `READY`.

### Layer Responsibilities

| Layer | Responsibility |
|---|---|
| `agents/` | LLM-driven reasoning; each agent calls `AIService.generate()` via its service |
| `workflow/` | LangGraph graph construction (`WorkflowBuilder`), compilation and execution (`LangGraphEngine`), and node definitions (`workflow/nodes/`) |
| `services/` | Domain generators (testcase, automation, database, summary, review, correction, planning); each owns its generation logic and delegates prompt construction to `PromptBuilder` |
| `ai/` | Provider-independent LLM infrastructure: `AIService`, `PromptBuilder`, `ContextBuilder`, `AgentProfile`, `LLMRequest`/`LLMResponse`, token tracking, cost calculation |
| `providers/` | Thin provider wrappers (`GroqProvider`, `ClaudeCLIProvider`, `OllamaProvider`) that translate `LLMRequest` + `AgentProfile` into provider-specific API/CLI calls and return a standard `LLMResponse` |
| `registries/` | `ProviderRegistry` (maps name → provider instance), `AgentProfileRegistry` (maps agent name → model/temperature/token config), `AgentRegistry`, `NodeRegistry`, `ToolRegistry` |
| `memory/` | Persistent SQLite store, episodic + procedural memory, embedding-based retrieval, `MemoryContextService` that injects retrieved memories into prompts as RAG context |
| `prompts/` | Prompt implementations per agent/capability; receive pre-built context strings and return `(system_prompt, user_prompt)` tuples |
| `models/` | Plain data models (`State`, `WorkflowState`, `Task`, `Plan`, `Artifact`, `Requirement`, etc.) |
| `constants/` | `AgentNames` and `PromptNames` enums used as registry keys throughout |

### AIService and Provider Selection

`AIService.generate(agent_name, request)` is the single call-site for all LLM generation. It:
1. Looks up the `AgentProfile` from `AgentProfileRegistry` by `agent_name`
2. Resolves the active provider from `ProviderRegistry` using `LLM_PROVIDER`
3. Retries on `AIRateLimitError` with exponential backoff (max 3 attempts)
4. Calculates cost via `PricingService` and attaches it to the response

Model selection precedence: `MODEL_NAME` env var → provider default in `AgentProfileRegistry._PROVIDER_DEFAULT_MODELS` → legacy fallback.

### Claude CLI Provider

`ClaudeCLIProvider` routes LLM calls through the locally available Claude Code CLI instead of calling the Anthropic API directly.

The runtime flow is:

```text
QAgentic
  → ClaudeCLIProvider
  → Claude Code CLI
  → Company Code Server / MARS
  → Claude
```

The company-specific OIDC/MARS setup is a prerequisite for using the Claude CLI provider and remains outside the core QAgentic provider abstraction.

### Memory and RAG

`MemoryContextService.build()` is called by `PromptBuilder` before every prompt construction. It retrieves semantically relevant episodic and procedural memories via `MemoryRetriever`, which uses `SentenceTransformerEmbeddingProvider` (model `all-MiniLM-L6-v2`) for cosine similarity, filters by `MemoryPolicy.minimum_confidence` (0.7), and returns the top-K results as a formatted context string injected into the prompt.

Default procedures are seeded at startup in `memory/procedural/default_procedures.py`. Episodic memories are captured after each successful execution in `EpisodeService.capture_execution()`.

The SQLite database file is `memory.db` in the working directory.

### Adding a New Provider

1. Create `providers/<name>_provider.py` implementing `BaseProvider.generate(request, profile) -> LLMResponse`
2. Register it in `ProviderRegistry._register_default_providers()`
3. Add a default model in `AgentProfileRegistry._PROVIDER_DEFAULT_MODELS`
4. Add the env key to `.env.example` and `config.py`

### Adding a New Capability / Generator

1. Add the capability name to `constants/agent_names.py` (or `constants/prompt_names.py`)
2. Create `services/<capability>_service.py` with the generation logic
3. Create `prompts/<capability>_prompt.py` returning `(system_prompt, user_prompt)`
4. Add a `PromptBuilder` method that wires context + memory → prompt function
5. Register an `AgentProfile` in `AgentProfileRegistry._register_default_profiles()`
6. Add a workflow node in `workflow/nodes/` and register it in `NodeRegistry`
