# 🚀 QAgentic

<div align="center">

### AI-Powered Workflow Framework for QA Engineering

Transform software requirements into high-quality QA deliverables using intelligent planning, workflow orchestration, AI review, automatic correction, and artifact publishing.

**Current Version: `v0.6.0`**

</div>

---

## 📖 Overview

QAgentic is a workflow-driven AI framework designed to automate the QA engineering lifecycle.

The framework accepts a software requirement, analyzes its intent, creates an execution plan, resolves task dependencies, executes QA tasks, reviews generated artifacts, automatically corrects failed artifacts, and publishes approved results.

The framework is built around modular agents, workflow orchestration, provider-independent LLM infrastructure, centralized prompt construction, dependency-aware execution, persistent memory, semantic retrieval, and RAG-based knowledge reuse.

---

# ✨ Key Features

## 🧠 Requirement Intelligence

* Requirement analysis
* Intent extraction
* Requirement readiness evaluation
* Interactive clarification
* Requirement re-analysis

## 🤖 AI QA Generation

* Requirement summary generation
* Functional test case generation
* Automation script generation
* Database-related artifact generation
* Generator-specific prompt builders

## ⚙️ Workflow Engine

* LangGraph-based workflow orchestration
* Modular workflow nodes
* Dependency-aware task planning
* Sequential dependency execution
* Parallel execution of independent tasks
* Workflow state management
* Artifact publishing

## 🔍 AI Quality Loop

* AI-generated artifact review
* Automatic correction
* Review → Correction → Review loop
* Quality feedback propagation
* Retry handling

## 🌐 MCP Tool Execution

* Model Context Protocol (MCP) client integration
* MCP tool discovery per server
* Stateful MCP session execution
* MCP guardrail evaluation
* Tool authorization policy enforcement
* Human approval boundary for write operations
* GitHub MCP integration (PR creation, repository operations)
* Playwright MCP integration (browser automation)

## 🔍 Page Inspection

* Playwright MCP primary strategy (live DOM snapshot)
* HTTP fallback strategy (direct HTML fetch and parse)
* `PAGE_INSPECTION_STRATEGY` environment variable (`mcp` / `http`)
* HTML structure extraction (title, headings, forms, inputs, buttons, links)
* DOM snapshot injection into test case and automation prompts
* Graceful degradation when both strategies fail

## ▶️ Test Execution

* Local subprocess-based test execution
* Framework-agnostic command runner
* Universal dependency pre-flight (npm, pip, bundler, go, dotnet)
* JDK auto-discovery and `JAVA_HOME` patching
* Playwright command normalisation (headless, reporter)
* Execution timeout with full process tree cleanup
* Execution output capture via temp files (avoids pipe inheritance hang)

## 🔧 Self-Healing

* Automatic failure diagnosis (COMPILE / SELECTOR / ASSERTION / TIMEOUT / CONFIG / OTHER)
* Failure investigation and root-cause analysis
* Full artifact regeneration when self-healing cannot patch in place
* Proactive dependency pre-flight prevents CONFIG failures before they occur

## 📁 Repository Operations

* Repository capability with MCP-backed execution
* GitHub MCP: PR creation, branch listing, repository inspection
* Local-path resolution → git remote URL discovery → platform routing
* Automatic enrichment of owner, head branch, base branch, and PR title from local git
* Checkpoint-based resume for multi-step repository plans
* Human approval boundary before write operations

## 🤖 Repository Analysis

* Static repository structure analysis
* Test file discovery
* Framework detection
* Language and build-tool identification
* Token-budget-aware analysis

## 🏗️ AI Infrastructure

* Centralized `AIService`
* Provider abstraction
* `ProviderRegistry`
* `AgentProfileRegistry`
* Standardized `LLMRequest`
* Standardized `LLMResponse`
* Centralized `PromptBuilder`
* Centralized `ContextBuilder`
* Provider-independent token tracking
* Model-based LLM pricing
* Per-request LLM cost calculation
* Provider-independent rate-limit handling
* Retry and backoff handling

## 🧠 Knowledge & RAG

* Persistent memory storage using SQLite
* Episodic memory
* Procedural memory
* Embedding-based semantic retrieval
* Semantic similarity search
* Relevance threshold filtering
* Top-K retrieval
* Capability-aware memory queries
* Retrieved memory context construction
* RAG context injection into LLM prompts
* Reusable knowledge across executions

---

# 🏛️ Architecture

The v0.6 architecture extends the v0.5 foundation with MCP tool execution, browser-based page inspection, autonomous test execution, universal dependency management, self-healing, repository operations, and a Claude CLI provider.

```mermaid
flowchart TD

A["User Requirement"]
B["Supervisor Agent"]
C["Workflow Manager"]
D["LangGraph Engine"]
E["Workflow Nodes"]
F["Agents"]
G["Generators / Services"]
H["PromptBuilder"]
I["ContextBuilder"]

J["Memory Context Service"]
K["Memory Manager"]
L["Memory Retriever"]
M["Embedding Provider"]
N["SQLite Memory Store"]

O["AIService"]
P["ProviderRegistry"]
Q["AgentProfileRegistry"]

R["Groq Provider"]
S["Ollama Provider"]
S2["Claude CLI Provider"]

T["LLMResponse"]
U["TokenUsage"]
V["LLMCost"]

CAP["Capabilities"]
PI["Page Inspection"]
TE["Test Execution"]
REPO["Repository"]
SH["Self-Healing"]

MCP["MCP Tool Executor"]
GH["GitHub MCP"]
PW["Playwright MCP"]

A --> B
B --> C
C --> D
D --> E
E --> F
F --> G
G --> H
H --> I

I --> J
J --> K
K --> L
L --> M
L --> N

J --> O

O --> P
O --> Q

P --> R
P --> S
P --> S2

R --> T
S --> T
S2 --> T

T --> U
T --> V

F --> CAP
CAP --> PI
CAP --> TE
CAP --> REPO
CAP --> SH

PI --> MCP
REPO --> MCP
MCP --> GH
MCP --> PW
```

---

# 🔄 End-to-End Workflow

```mermaid
flowchart TD

A["Requirement"]

B["Requirement Intelligence"]

C{"Requirement Ready?"}

D["Clarification"]

E["Re-analysis"]

F["Planner"]

G["Execution"]

H["Review"]

I{"Quality Passed?"}

J["Correction"]

K["Publish"]

A --> B
B --> C

C -- "No" --> D
D --> E
E --> C

C -- "Yes" --> F
F --> G
G --> H
H --> I

I -- "No" --> J
J --> H

I -- "Yes" --> K
```

---

# 🧩 AI Request Architecture

The framework uses provider-independent request and response models.

## LLMRequest

`LLMRequest` represents the information sent to an LLM provider:

```text
LLMRequest
├── system_prompt
├── user_prompt
└── metadata
```

The request model is provider agnostic.

## AgentProfile

`AgentProfile` contains agent-specific model configuration:

```text
AgentProfile
├── agent_name
├── model
├── temperature
└── response_format
```

The provider translates these settings into its own API format.

## LLMResponse

Every provider returns the common response structure:

```text
LLMResponse
├── content
├── provider
├── model
├── token_usage
├── cost
└── metadata
```

This prevents agents and generators from depending on provider-specific response objects.

---

# 🧠 Knowledge & RAG Architecture

QAgentic uses a Retrieval-Augmented Generation (RAG) layer to provide relevant previously stored knowledge to agents during execution.

```text
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
Semantic Similarity
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
```

The v0.5 memory layer uses SQLite for persistent storage and embedding-based semantic retrieval.

Retrieved memories are supporting context for generation and are not treated as new user requirements.

## Memory Types

### Episodic Memory

Stores information related to previous execution experiences, outcomes, and relevant runtime history.

### Procedural Memory

Stores reusable QA knowledge, workflow knowledge, and patterns that can help future executions.

## Retrieval

Memory retrieval uses semantic similarity between the current query and stored memories.

```text
Query
  ↓
Query Embedding
  ↓
Candidate Memories
  ↓
Similarity Calculation
  ↓
Relevance Threshold
  ↓
Ranking
  ↓
Top-K Results
  ↓
Memory Context
```

This allows the framework to reuse relevant knowledge without requiring exact keyword matches.

---

# 💰 Token & Cost Tracking

The framework provides centralized LLM usage and cost tracking.

Each successful LLM request can capture:

```text
Input Tokens
Output Tokens
Total Tokens
```

The framework then resolves model pricing and calculates:

```text
Input Cost
Output Cost
Total Cost
```

The provider is responsible for extracting actual token usage.

The centralized AI infrastructure is responsible for calculating cost.

This keeps provider implementations independent from pricing logic.

---

# 🔌 Provider Architecture

Providers implement a common contract:

```python
generate(
    request: LLMRequest,
    profile: AgentProfile
) -> LLMResponse
```

The current provider implementations include:

| Provider                |    Status   |
| ----------------------- | :---------: |
| Groq                    |      ✅      |
| Ollama                  |      ✅      |
| Claude CLI (MARS/OIDC)  |      ✅      |
| Google Gemini           |  Available  |
| OpenAI                  |   Planned   |
| Azure OpenAI            |   Planned   |

The provider abstraction allows the workflow and agents to remain independent of the underlying LLM provider.

---

# 🧠 Prompt & Context Architecture

Prompt construction is separated from agent execution.

```text
Agent
  ↓
PromptBuilder
  ↓
ContextBuilder
  ↓
System Prompt + User Prompt
  ↓
LLMRequest
  ↓
AIService
```

Individual prompt builders are responsible for their specific agent/task requirements.

The `ContextBuilder` prepares runtime domain information before it reaches the prompt layer.

This prevents agents from directly assembling large provider-specific requests.

---

# 📁 Project Structure

```text
QAgentic/
│
├── agents/
│   ├── base_agent.py
│   ├── execution_agent.py
│   ├── planner_agent.py
│   ├── requirement_agent.py
│   ├── requirement_intelligence_agent.py
│   ├── review_agent.py
│   ├── self_healing_agent.py          ← v0.6
│   └── supervisor_agent.py
│
├── ai/
│   ├── builders/
│   │   ├── context_builder.py
│   │   └── prompt_builder.py
│   │
│   ├── config/
│   │   ├── llm_cost.py
│   │   ├── model_pricing.py
│   │   └── pricing_config.py
│   │
│   ├── models/
│   │   ├── llm_request.py
│   │   └── llm_response.py
│   │
│   ├── profiles/
│   │   └── agent_profile.py
│   │
│   ├── prompts/
│   │   ├── prompt_result.py
│   │   └── prompt_template.py
│   │
│   ├── services/
│   │   ├── ai_service.py
│   │   └── pricing_service.py
│   │
│   └── token/
│       ├── token_manager.py
│       └── token_usage.py
│
├── capabilities/
│   ├── base_capability.py
│   ├── code_push/                     ← v0.6
│   ├── page_inspection/               ← v0.6
│   ├── repository/                    ← v0.6
│   ├── repository_analysis/           ← v0.6
│   ├── test_execution/                ← v0.6
│   └── test_gap_analysis/             ← v0.6
│
├── infrastructure/
│   ├── execution/
│   │   └── local/
│   │       └── local_execution_provider.py   ← v0.6
│   └── repository/
│       ├── git/
│       └── mcp/
│           └── mcp_repository_provider.py    ← v0.6
│
├── mcp_integration/
│   ├── guardrails/                    ← v0.6
│   └── tool/
│       └── mcp_tool_executor.py       ← v0.6
│
├── memory/
│   ├── embeddings/
│   ├── episodic/
│   ├── models/
│   ├── procedural/
│   └── stores/
│
├── artifacts/
├── bootstrap/
├── constants/
├── domain/
├── models/
├── prompts/
├── providers/
│   ├── claude_cli_provider.py         ← v0.6
│   ├── groq_provider.py
│   └── ollama_provider.py
├── registries/
├── services/
├── utils/
│
├── workflow/
│   ├── nodes/
│   └── workflow_routers/
│
├── app.py
├── config.py
├── requirements.txt
├── CHANGELOG.md
└── LICENSE
```

---

# ⚙️ Requirements

* Python 3.12+
* Dependencies listed in `requirements.txt`
* At least one configured LLM provider
* SQLite for persistent local memory
* Embedding model support for semantic memory retrieval

---

# 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/QAgentic.git
cd QAgentic
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 🔐 Configuration

Create a local `.env` file using `.env.example` as the template.

Example:

```properties
LLM_PROVIDER=groq

# Groq
GROQ_API_KEY=

# Google Gemini
GEMINI_API_KEY=

# Ollama - required when using Ollama
OLLAMA_URL=http://localhost:11434/api/generate
MODEL_NAME=

# Claude CLI (MARS/OIDC) — no API key required; uses locally installed Claude Code CLI
# LLM_PROVIDER=claude_cli

# Logging
LOG_LEVEL=INFO

# Output
OUTPUT_FOLDER=generated

# Page inspection strategy: mcp (default) or http
# mcp  — uses Playwright MCP, falls back to HTTP if MCP fails
# http — skips Playwright and fetches page HTML directly via requests
PAGE_INSPECTION_STRATEGY=mcp

# Test execution timeout in seconds (default: 300)
EXECUTION_TIMEOUT_SECONDS=1800
```

Never commit `.env` or API credentials to Git.

---

# ▶️ Running the Framework

```bash
python app.py
```

QAgentic can execute the complete QA workflow:

```text
Requirement
    ↓
Requirement Intelligence
    ↓
Clarification when required
    ↓
Planning
    ↓
Task Execution
    ↓
Memory / RAG Context
    ↓
Artifact Review
    ↓
Correction when required
    ↓
Re-review
    ↓
Artifact Publishing
```

---

# 📊 v0.6 Architecture Highlights

Version `0.6.0` delivers the end-to-end execution pipeline: live page inspection, automated test execution, self-healing, repository operations via MCP, and the Claude CLI provider.

### Added

* MCP tool executor with server discovery and stateful session execution
* MCP guardrail and tool authorization policy
* Page inspection capability (Playwright MCP primary + HTTP fallback)
* DOM snapshot extraction and injection into test case and automation prompts
* Test execution capability with local subprocess runner
* Universal dependency pre-flight (npm, pip, bundler, go, dotnet)
* JDK auto-discovery and `JAVA_HOME` patching for Java/Maven/Gradle projects
* Playwright command normalisation (strip `--headed`, inject `--reporter=line`)
* Execution timeout with full process tree cleanup on Windows
* Self-healing agent (COMPILE / SELECTOR / ASSERTION / TIMEOUT / CONFIG / OTHER)
* Repository capability with MCP-backed execution and checkpoint resume
* GitHub MCP integration (PR creation, repository operations)
* Local-path → git remote URL discovery for repository routing
* Automatic PR enrichment (owner, head branch, base branch, title) from local git
* Repository analysis capability (structure, framework, language detection)
* Test gap analysis capability
* Code push capability
* Claude CLI provider (`claude_cli`) routing through company MARS/OIDC environment
* `PAGE_INSPECTION_STRATEGY` environment variable (`mcp` / `http`)
* `EXECUTION_TIMEOUT_SECONDS` environment variable

### Improved

* Requirement intelligence constrained to emit only valid `execution_mode` values (`mcp` / `local`)
* Automation prompt includes stealth browser args to reduce bot-detection blocks
* Automation prompt enforces dependency install steps in `run_command` for all frameworks
* DOM snapshot cleanly separated from general dependency context in prompts
* Provider table extended with Claude CLI

---

# 📊 v0.5 Architecture Highlights

Version `0.5.0` introduced the Knowledge and RAG foundation.

### Added

* Persistent SQLite memory
* Episodic memory
* Procedural memory
* Memory models and policies
* Embedding-based semantic retrieval
* Similarity-based relevance filtering
* Top-K retrieval
* Capability-aware memory queries
* Memory context construction
* RAG context integration with agent prompts
* Reusable knowledge across executions
* Provider-independent rate-limit handling
* Retry and backoff support

### Improved

* Context-aware agent generation
* Separation of stored knowledge from runtime requirements
* Semantic retrieval instead of exact keyword-only matching
* Centralized memory context construction
* Provider-independent AI infrastructure

---

# ⚠️ Known Limitations

* Akamai / Cloudflare-protected sites (e.g. Meesho) block both headless Playwright and HTTP page inspection. Use `automationexercise.com` or similar unprotected sites for end-to-end pipeline verification.
* GitHub MCP requires the GitHub MCP server to be configured and authenticated in the local Claude Code MCP environment.
* The Claude CLI provider requires the company MARS/OIDC environment setup to be completed before use.
* External repository/document indexing is not included in v0.6.
* Advanced external knowledge sources are planned for future versions.

---

# 🗺️ Roadmap

| Version | Status | Focus |
| ------- | :----: | ----- |
| v0.1.0 |    ✅   | Initial AI QA framework |
| v0.2.0 |    ✅   | Planning, review and parallel execution |
| v0.3.0 |    ✅   | LangGraph workflow, application container and workflow nodes |
| v0.4.0 |    ✅   | AI infrastructure, provider abstraction, agent profiles, prompt/context architecture, token and cost tracking |
| v0.5.0 |    ✅   | Knowledge, memory, embeddings and RAG foundation |
| v0.6.0 |    ✅   | MCP, tool execution, page inspection, test execution, self-healing, repository operations, Claude CLI provider |
| v0.7.0 |    🚧   | Intelligent QA capabilities |
| v0.8.0 |    🚧   | Enterprise integrations |
| v0.9.0 |    🚧   | Advanced QA intelligence |
| v1.0.0 |    🎯   | Production AI-QA platform |

## v0.7 — Intelligent QA Capabilities

Planned capabilities include:

* UI ↔ Database Validation Capability
* Failure Diagnosis Capability
* CI/CD Pipeline Recovery Capability
* Kafka / Staging Validation Capability
* Appium mobile test support

Capabilities may internally use agents, services, tools, MCP integrations, and retrieved knowledge.

### Terminology

**Capability**

A QA operation that the platform can perform.

**Agent**

An LLM-driven reasoning component that may implement part of a capability.

**Tool / MCP**

The mechanism through which agents interact with external systems.

**RAG / Knowledge Layer**

The mechanism used to retrieve relevant stored knowledge and provide it as context during reasoning.

---

# 🤝 Contributing

Contributions, feature requests, bug reports, and discussions are welcome.

If you'd like to contribute:

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add or update tests where applicable
5. Commit your changes
6. Submit a Pull Request

---

# 📄 License

This project is licensed under the MIT License.

See the `LICENSE` file for complete details.
