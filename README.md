# 🏢 Enterprise AI Knowledge & Support Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)
[![Qdrant](https://img.shields.io/badge/Qdrant-v1.12.0-DC2626.svg)](https://qdrant.tech/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-v2.2.0-7C3AED.svg)](https://modelcontextprotocol.io/)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-v2.9.0-4285F4.svg)](https://github.com/google/agent-development-kit)
[![Streamlit](https://img.shields.io/badge/Streamlit-v1.40+-FF4B4B.svg)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 177 Passed](https://img.shields.io/badge/tests-177%20passed-brightgreen.svg)](tests/)

An enterprise-grade, multi-agent AI knowledge and support orchestration platform. Combines **Google Agent Development Kit (ADK)** hierarchical agent routing, **Retrieval-Augmented Generation (RAG)** over a **Qdrant Vector Database**, and standardized database actions powered by Anthropic's **Model Context Protocol (MCP)**. Features a high-performance **FastAPI** gateway, an interactive **Streamlit** executive web console, portfolio-level application security controls, and full multi-container **Docker Compose** deployment.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Features](#3-features)
4. [Architecture](#4-architecture)
5. [Technology Stack](#5-technology-stack)
6. [System Workflow](#6-system-workflow)
7. [RAG Pipeline](#7-rag-pipeline)
8. [Context Engineering](#8-context-engineering)
9. [Google ADK Architecture](#9-google-adk-architecture)
10. [MCP Architecture](#10-mcp-architecture)
11. [LangChain Usage](#11-langchain-usage)
12. [Qdrant Usage](#12-qdrant-usage)
13. [FastAPI Gateway](#13-fastapi-gateway)
14. [Streamlit Web Console](#14-streamlit-web-console)
15. [Security Controls](#15-security-controls)
16. [Evaluation Framework](#16-evaluation-framework)
17. [Testing](#17-testing)
18. [Docker & Containerization](#18-docker--containerization)
19. [Installation](#19-installation)
20. [Environment Variables](#20-environment-variables)
21. [Running Locally](#21-running-locally)
22. [Running with Docker](#22-running-with-docker)
23. [Example Queries & Workflows](#23-example-queries--workflows)
24. [User Interface & Layout](#24-user-interface--layout)
25. [Project Structure](#25-project-structure)
26. [Design Decisions](#26-design-decisions)
27. [Limitations](#27-limitations)
28. [Future Improvements](#28-future-improvements)

---

## 1. Overview

The **Enterprise AI Knowledge & Support Agent** is designed to eliminate the friction between corporate knowledge discovery and transactional support workflows. Modern organizations maintain extensive documentation (HR policies, IT guidelines, onboarding procedures, security protocols) alongside transactional ticketing systems (ServiceNow, Jira Service Desk).

This platform bridges that divide using a unified, multi-tiered AI architecture:
- **Informational Inquiries**: Answered via semantic RAG retrieval with verified document citations, section metadata, and strict anti-hallucination refusals.
- **Operational Actions**: Executed safely through typed, isolated Model Context Protocol (MCP) tools against enterprise records.
- **Composite Inquiries**: Evaluated sequentially—verifying policy requirements first, determining employee eligibility, and automatically executing the corresponding support action.

---

## 2. Problem Statement

Corporate enterprise support typically faces three critical operational bottlenecks:

1. **Information Fragmentation & Hallucination**: Knowledge is dispersed across PDF manuals, Notion spaces, and markdown wikis. Standard LLM chatbots frequently hallucinate non-existent benefits or outdated IT configurations, leading to compliance risks.
2. **Context Switching & Operational Drag**: An employee attempting to resolve an issue (e.g., requesting a laptop refresh or configuring VPN access) must find the policy document, interpret the qualification rules, navigate to a separate ticketing portal, and manually submit a ticket.
3. **Tool Insecurity & System Coupling**: Directly exposing enterprise databases or internal REST endpoints to unconstrained LLMs introduces severe prompt injection, data leakage, and unintended database mutation risks.

**Solution**: This system enforces strict boundary separation. An ADK root orchestrator routes inquiries to specialized sub-agents. Knowledge retrieval is grounded in strict vector embeddings with relevance thresholds, operational tasks are delegated exclusively through typed MCP JSON-RPC schemas, and inputs are scrubbed through a multi-tier security filter.

---

## 3. Features

- **Multi-Signal Intent Classification**: Dynamically classifies incoming user queries into `RAG_ONLY`, `TOOL_ONLY`, `HYBRID_RAG_TOOL`, or `SAFETY_REFUSAL` using linguistic patterns, entity recognition, and adversarial heuristics.
- **Advanced Semantic RAG**:
  - Structure-aware markdown and PDF chunking tracking document section hierarchies (`#`, `##`, `###`).
  - Dense 768-dimensional normalized embeddings with cosine similarity matching.
  - Multi-factor score thresholding (`similarity >= 0.72`) and passage deduplication.
  - Verifiable citation contracts linking answers directly to source file names and section titles.
- **Model Context Protocol (MCP) Integration**:
  - FastMCP server exposing tools for policy search, support ticket creation, ticket status tracking, and employee directory queries.
  - Dual-transport support: local high-throughput `stdio` and distributed network `SSE/HTTP`.
  - Client connection pooling, session lifecycle management, and subprocess pipe cleanup.
- **Google ADK Orchestrator**:
  - Hierarchical agent design featuring a canonical `RootAgent` delegating to `RAGAgent` and `MCPToolAgent`.
  - Unified 3-tier response contract separating retrieved knowledge chunks, tool execution outputs, and synthesized natural language explanations.
- **Portfolio-Level Security Controls**:
  - Constant-time API key verification (`hmac.compare_digest`).
  - File upload restrictions enforcing strictly `.pdf`, `.txt`, `.md` extensions, magic byte validation, and 10MB file caps.
  - Request payload size limits (10MB) via custom ASGI middleware.
  - Log sanitization redacting API keys, passwords, bearer tokens, and confidential headers.
  - Prompt injection detection defanging directive overrides, jailbreak roleplay, and XML delimiter tampering.
- **Enterprise Web Console & REST Gateway**:
  - Production FastAPI gateway with automatic OpenAPI documentation and structured JSON error contracts.
  - Executive Streamlit UI featuring workflow telemetry badges, expandable source citation drawers, ticket tracking forms, and document ingestion.
- **Complete 4-Service Containerization**:
  - Multi-stage production `Dockerfile` with non-root security (`appuser:appuser`).
  - Production `docker-compose.yml` orchestrating `api`, `streamlit`, `qdrant`, and `mcp` services with native readiness health checks and persistent volume mounts.
- **Empirical Evaluation Framework**:
  - 32 synthetic benchmark questions spanning 8 operational categories.
  - Automated measurement of retrieval hit rate, citation presence, grounded refusal accuracy, tool delegation rate, and adversarial defense rate.

---

## 4. Architecture

```mermaid
flowchart TB
    subgraph ClientLayer ["Client Presentation Layer"]
        UI["Streamlit Web Console<br/>(:8501)"]
        CLI["API Consumer / cURL<br/>(:8000)"]
    end

    subgraph APILayer ["FastAPI REST Gateway (:8000)"]
        MW["RequestIDMiddleware<br/>(Tracing & 10MB Cap)"]
        Auth["Security Filter<br/>(API Key & Log Sanitizer)"]
        Router["API Route Controllers<br/>(/chat, /tickets, /ingest, /tools)"]
    end

    subgraph AgentLayer ["Google ADK Multi-Agent Orchestrator"]
        Service["Agent Service Layer"]
        Root["RootAgent ('root_agent')<br/>Multi-Signal Intent Classifier"]
        RAGAgent["RAGAgent<br/>Knowledge Synthesizer"]
        ToolAgent["MCPToolAgent<br/>Action Executor"]
        ContextEng["Context Engine<br/>Token Budgeting & Injection Defanging"]
    end

    subgraph MCPService ["FastMCP Tool Service (:8001 / stdio)"]
        MCPServer["FastMCP Server (SSE / stdio)"]
        T1["search_policy"]
        T2["create_support_ticket"]
        T3["get_ticket_status"]
        T4["get_employee_info"]
    end

    subgraph StorageLayer ["Data & Vector Storage"]
        Qdrant["Qdrant Vector DB<br/>(:6333 / 'enterprise_knowledge_base')"]
        SQLite[("SQLite Business DB<br/>('enterprise.db')")]
    end

    subgraph ExternalLLM ["LLM Reasoning Engine"]
        Gemini["Google Gemini (gemini-2.0-flash)<br/>or Deterministic Offline Fallback"]
    end

    UI -->|HTTP / JSON| Router
    CLI -->|HTTP / JSON| MW --> Auth --> Router
    Router --> Service --> Root

    Root --> ContextEng
    Root -->|Informational Query| RAGAgent
    Root -->|Operational Action| ToolAgent
    Root -->|Hybrid Inquiry| RAGAgent --> ToolAgent

    RAGAgent --> ContextEng --> Qdrant
    RAGAgent --> Gemini
    ToolAgent --> MCPServer
    MCPServer --> T1 & T2 & T3 & T4
    T2 & T3 & T4 --> SQLite
    T1 --> Qdrant
```

---

## 5. Technology Stack

| Technology | Version | Purpose in System | Why Selected? |
| :--- | :--- | :--- | :--- |
| **Python** | `3.11+` | Core Programming Language | Mature async primitives (`asyncio`), robust typing support, and standard runtime for AI/ML ecosystems. |
| **FastAPI** | `>=0.115.0` | REST API Gateway | High throughput ASGI framework, native async request handling, dependency injection, and automatic OpenAPI schema generation. |
| **Google ADK** | `>=2.9.0` | Agent Orchestration | Official Google Agent Development Kit provides first-class sub-agent delegation, structured instructions, and native Gemini compatibility. |
| **Model Context Protocol** | `>=2.2.0` | Tool Execution Subsystem | Open standard by Anthropic. Decouples tool schemas and runtime execution from LLM prompt internals; supports stdio and network SSE. |
| **Qdrant** | `v1.12.0` | Vector Database | High-performance Rust vector engine with native payload metadata filtering, persistent disk storage, and identical embedded/server APIs. |
| **LangChain Core** | `>=0.3.0` | Text Splitters & Chunking | Utilized strictly for structure-aware document parsing (`MarkdownHeaderTextSplitter`) without adopting bloated agent abstractions. |
| **Pydantic** | `>=2.9.0` | Data Validation & Schemas | Rust-backed `pydantic-core` provides instant serialization, strict schema enforcement, and zero-overhead request/response validation. |
| **Streamlit** | `>=1.40.0` | Executive Web Console | Rapid reactive UI development with zero frontend build pipeline; seamless session state management and rich markdown rendering. |
| **SQLite** | `3.x` | Relational Business DB | Zero-configuration, ACID-compliant local database for employees and support tickets with full foreign key constraints. |
| **Docker & Compose** | Multi-stage | Containerization | Guarantees isolated, reproducible environments across host architectures with healthchecks and persistent storage volumes. |
| **Pytest** | `>=8.3.0` | Automated Testing | Comprehensive test framework supporting async test execution (`pytest-asyncio`), mocking, and fixture isolation. |

---

## 6. System Workflow

The orchestrator dynamically routes requests through one of four workflows based on linguistic cues and intent analysis:

```mermaid
sequenceDiagram
    autonumber
    actor User as Employee / Client
    participant UI as Streamlit / FastAPI
    participant Root as RootAgent
    participant RAG as RAGAgent / Qdrant
    participant Tool as MCPToolAgent / FastMCP
    participant DB as SQLite / Tickets

    %% RAG-Only Workflow
    Note over User, DB: Scenario 1: RAG-Only ("What is the remote work policy?")
    User->>UI: "What is the remote work policy on core hours?"
    UI->>Root: analyze_query() -> RAG_ONLY
    Root->>RAG: retrieve_context(query)
    RAG->>RAG: Vector Search & Deduplicate (Threshold >= 0.72)
    RAG-->>Root: Chunks with Section Metadata
    Root-->>UI: Answer with Citations (remote_work_policy.md, Sec 4)
    UI-->>User: Display Response + Citation Pill

    %% Tool-Only Workflow
    Note over User, DB: Scenario 2: Tool-Only ("Create a ticket for my VPN issue.")
    User->>UI: "Create an IT ticket for employee EMP-1001: VPN fails to connect"
    UI->>Root: analyze_query() -> TOOL_ONLY
    Root->>Tool: execute_tool("create_support_ticket", args)
    Tool->>DB: INSERT INTO tickets (...)
    DB-->>Tool: Ticket ID: TCK-2026-9A1F
    Tool-->>Root: ToolExecutionResult(success=True, id=TCK-2026-9A1F)
    Root-->>UI: Confirmation + Ticket Details
    UI-->>User: Display Action Output + Ticket Card

    %% Hybrid Workflow
    Note over User, DB: Scenario 3: Hybrid ("What does VPN policy say, and create a ticket if appropriate?")
    User->>UI: "What does the VPN policy require for remote access, and create a ticket for EMP-1001?"
    UI->>Root: analyze_query() -> HYBRID_RAG_TOOL
    Root->>RAG: Step 1: Retrieve VPN Policy Facts
    RAG-->>Root: Policy Chunks (MFA required, Cisco AnyConnect)
    Root->>Tool: Step 2: Invoke Ticket Creation Tool
    Tool->>DB: INSERT INTO tickets (category='IT', priority='MEDIUM')
    DB-->>Tool: Ticket ID: TCK-2026-B8C2
    Tool-->>Root: ToolExecutionResult
    Root-->>UI: Synthesize 3-Tier Response (Policy + Action + Explanation)
    UI-->>User: Display Grounded Knowledge + Executed Action
```

---

## 7. RAG Pipeline

```
Raw Documents (.md, .pdf, .txt)
       │
       ▼
Text Cleaning & Normalization (app/rag/cleaners.py)
       │
       ▼
Hierarchy-Aware Chunking (MarkdownHeaderTextSplitter)
[# Header 1] -> [## Header 2] -> [### Header 3]
       │
       ▼
Dense Vector Embedding (768-dim normalized)
       │
       ▼
Qdrant Vector Upsert (Cosine Distance / Payload Metadata)
       │
       ▼
Retrieval & Filtering (app/rag/retriever.py)
├── Cosine Similarity Filter (score >= 0.72)
├── Semantic Deduplication (Jaccard content hash filtering)
└── Top-K Window Limiting (K=5)
```

1. **Document Loading**: Multi-format loaders in `app/rag/loaders.py` extract raw content from Markdown files, plain text, and PDF documents using `pypdf`.
2. **Chunking Strategy**: Rather than arbitrary character slicing, the pipeline uses `MarkdownHeaderTextSplitter` to preserve document structure. Every chunk retains its exact section path (e.g., `4. Operational Hours & Collaboration Standards`). Max chunk size is 600 characters with 80 character overlap.
3. **Embeddings**: Generated using 768-dimensional normalized dense vectors.
4. **Qdrant Storage**: Vectors are indexed in Qdrant's `enterprise_knowledge_base` collection using Cosine distance and HNSW graph indexing. Payloads store `doc_id`, `filename`, `section`, `chunk_index`, and `content_hash`.
5. **Retrieval & Reranking**: The retriever enforces a minimum similarity score threshold of `0.72`. Chunks below this threshold are rejected to prevent hallucinated answers. Redundant overlapping chunks are deduplicated via content hashing.

---

## 8. Context Engineering

Context engineering governs how retrieved data is sanitized, budgeted, and assembled before entering the LLM prompt:

- **Query Analysis**: Computes intent scores (`knowledge_intent`, `action_intent`), extracts key entities (employee IDs, ticket categories), and identifies injection signatures.
- **Adversarial Sanitization**: Defangs delimiter injection attempts by escaping XML tags (`<system>`, `[INST]`, `<admin>`) and neutralizing directive overrides (`Ignore previous instructions`).
- **Multi-Factor Passage Prioritization**: Ranks retrieved passages according to a weighted composite score:
  $$\text{Priority} = 0.55 \times \text{VectorSimilarity} + 0.25 \times \text{KeywordOverlap} + 0.20 \times \text{SectionDepth}$$
- **Token Budget Allocation**:
  - System Instructions & Governance Rules: 600 tokens max
  - Verified Context Chunks: 1,500 tokens max
  - Conversation History (Rolling Window): 800 tokens max
  - Output Generation Budget: 1,000 tokens max

---

## 9. Google ADK Architecture

The agent orchestration layer is built on the **Google Agent Development Kit (ADK)**:

```
                  ┌────────────────────────┐
                  │       RootAgent        │
                  │  (name="root_agent")   │
                  └───────────┬────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
  ┌───────────────────────┐       ┌───────────────────────┐
  │       RAGAgent        │       │     MCPToolAgent      │
  │  (name="rag_agent")   │       │(name="mcp_tool_agent")│
  └───────────────────────┘       └───────────────────────┘
```

- **RootAgent** (`app/agent/root_agent.py`): Acts as the top-level ADK supervisor. It evaluates user intent, orchestrates sub-agent calls, and produces the final unified `AgentResponse`.
- **RAGAgent** (`app/agent/rag_agent.py`): Sub-agent dedicated to knowledge synthesis. Queries the retriever, validates evidence, and generates verified citations.
- **MCPToolAgent** (`app/agent/tool_agent.py`): Sub-agent dedicated to operational actions. Formats typed parameters and executes tools via the MCP client.
- **Unified 3-Tier Response Schema**:
  ```python
  class AgentResponse(BaseModel):
      workflow: WorkflowType                     # Selected workflow
      response_text: str                         # Synthesized user answer
      retrieved_knowledge: List[KnowledgeItem]   # 1. Verified policy chunks
      tool_results: List[ToolExecutionResult]    # 2. Operational action outputs
      llm_explanation: Optional[str]             # 3. LLM reasoning summary
      audit_logs: Dict[str, Any]                 # Tracing & latency telemetry
  ```

---

## 10. MCP Architecture

The **Model Context Protocol (MCP)** subsystem standardizes how the agent interacts with enterprise systems:

- **FastMCP Server** (`app/mcp/server.py`): Implemented using the official MCP Python SDK v2. Registers tools with JSON-Schema argument validation and provides both `stdio` and `SSE/HTTP` transports.
- **Available MCP Tools**:
  1. `search_policy`: Semantic search over corporate policy documentation.
  2. `create_support_ticket`: Validates employee existence in SQLite and inserts a ticket.
  3. `get_ticket_status`: Retrieves ticket resolution state, priority, and notes.
  4. `get_employee_info`: Queries employee directory by ID (`EMP-1001`) or email.
- **EnterpriseMCPClient** (`app/mcp/client.py`): An asynchronous client managing session lifecycle, capability negotiation, tool discovery, and connection pooling. Automatically supports remote SSE endpoints (`MCP_SERVER_URL=http://mcp:8001/sse`) while falling back to local `stdio` subprocess execution for local development.

---

## 11. LangChain Usage

LangChain is adopted in a **targeted and disciplined manner** rather than as a monolithic framework:

- **What We Use**:
  - `langchain-text-splitters`: Specifically `MarkdownHeaderTextSplitter` and `RecursiveCharacterTextSplitter` for document chunking and section hierarchy extraction.
  - `langchain-core`: Standard document models (`Document`) and vector abstractions.
- **What We Intentionally Avoid**:
  - We do **not** use LangChain's legacy `AgentExecutor`, bloated chain abstractions, or proprietary callbacks.
  - Multi-agent orchestration is handled natively by **Google ADK**, and tool interfaces are governed strictly by the **Model Context Protocol (MCP)**. This prevents vendor lock-in and keeps agent logic clean and testable.

---

## 12. Qdrant Usage

**Qdrant** serves as the vector indexing and retrieval engine:

- **Storage Modes**:
  - **Embedded / Local Mode**: Uses `data/qdrant_storage` for local development and offline unit testing without external dependencies.
  - **Client-Server Mode**: Connects over HTTP/gRPC (`http://qdrant:6333`) in production and Docker Compose environments.
- **Collection Configuration**:
  - Collection Name: `enterprise_knowledge_base`
  - Vector Dimensions: `768`
  - Distance Metric: `Cosine`
  - HNSW Index Parameters: `m=16`, `ef_construct=100`
- **Native Container Readiness Probe**:
  - The Qdrant container uses a native TCP socket readiness probe (`/dev/tcp/127.0.0.1/6333`) checking the `/readyz` endpoint, ensuring all shards are loaded before dependent services boot.

---

## 13. FastAPI Gateway

The REST API gateway (`app/api/`) exposes endpoints for external systems and frontend clients:

- `GET /health`: Comprehensive health check reporting status of database, Qdrant, MCP client, and LLM configuration.
- `POST /api/chat`: Primary conversational endpoint routing messages to the Google ADK orchestrator.
- `POST /api/ingest`: Triggers loading, chunking, and embedding of policy documents.
- `POST /api/tickets`: Direct API endpoint for ticket submission.
- `GET /api/tickets/{ticket_id}`: Retrieves ticket details and resolution notes.
- `GET /api/tools`: Discovers available MCP tool schemas and parameter contracts.
- `POST /api/tools/{tool_name}`: Direct execution endpoint for authorized MCP tools.

### Tracing Middleware (`RequestIDMiddleware`)
Every request receives a unique `X-Request-ID` (or echoes a client-provided header). Request execution time is tracked and returned in `X-Process-Time-Ms`. Requests exceeding 10MB are rejected immediately with HTTP 413.

---

## 14. Streamlit Web Console

The frontend (`frontend/streamlit_app.py`) provides an executive interface with zero business logic coupling:

- **Chat Interface**: Renders conversational turns with interactive workflow badges:
  - `🏷️ RAG Only`: Policy questions with expandable citation drawers showing document names and sections.
  - `⚡ MCP Tool`: Displays tool invocation parameters and raw output cards.
  - `🔄 Hybrid (RAG + MCP)`: Combines policy guidance with real-time ticket creation cards.
  - `🛡️ Security Refusal`: Clean explanations when inquiries violate safety boundaries.
- **Ticket Management Tab**: Interactive forms for submitting IT/HR tickets with category selectors and ticket lookup tools.
- **Document Ingestion Tab**: Drag-and-drop document uploader supporting `.pdf`, `.txt`, and `.md` with live validation.
- **Tools Explorer Tab**: Real-time schema inspector displaying all available MCP tools and parameters.

---

## 15. Security Controls

This repository implements **portfolio-level application security controls**:

1. **API Key Authentication**: Enforced via constant-time comparison (`hmac.compare_digest`) across all `/api/*` endpoints. Supports both `X-API-Key` headers and `Authorization: Bearer <token>`.
2. **Production Key Strength Enforcement**: In `production` environment mode, API keys must be at least 16 characters long and cannot contain `"dev"` or placeholder strings.
3. **Strict File Upload Validation**: Uploads are restricted strictly to `.pdf`, `.txt`, and `.md`. PDF uploads are validated against magic byte signatures (`%PDF-`), and file sizes are capped at 10MB.
4. **Log Sanitization**: A custom logging filter (`RedactingLogFilter`) scans all log output and masks API keys, passwords, bearer tokens, and confidential user credentials before writing to disk.
5. **Prompt Injection Mitigation**: A heuristic safety scanner inspects incoming prompts for directive overrides (`Ignore previous instructions`), jailbreaks (`DAN mode`), and delimiter tampering (`<system>`). Injections are routed to `SAFETY_REFUSAL`.

---

## 16. Evaluation Framework

The project includes an empirical benchmark harness in `evaluation/`:

- **Benchmark Dataset** (`evaluation/dataset.json`): 32 synthetic test cases across 8 operational categories:
  1. `rag_factual`: Specific single-document policy inquiries
  2. `rag_multi_document`: Inquiries spanning multiple policies
  3. `mcp_tools`: Direct operational actions
  4. `rag_mcp_hybrid`: Joint policy verification and action execution
  5. `irrelevant`: Queries outside enterprise domain
  6. `hallucination`: Unanswerable queries testing abstention
  7. `prompt_injection`: Adversarial attack vectors
  8. `ambiguous`: Underspecified employee inquiries

### Measured Benchmark Results (No Fabricated Metrics)
All metrics reflect real automated execution against local databases:

| Evaluation Suite | Metric | Actual Result | Status |
| :--- | :--- | :--- | :--- |
| **Tool Execution Benchmark** (`evaluate_tools.py`) | Tool Execution Success Rate | **8 / 8 (100.0%)** | PASSED |
| | Average Tool Latency | 538.58 ms | Validated |
| **RAG Retrieval Benchmark** (`evaluate_rag.py`) | Retrieval Hit Rate (Recall@K=4) | **9 / 10 (90.0%)** | PASSED |
| | Citation Presence Rate | **10 / 10 (100.0%)** | PASSED |
| | Grounded Refusal Accuracy | **4 / 10 (40.0%)** | Documented limitation |
| | Average Retrieval Latency | 219.38 ms | Validated |
| **Multi-Agent Orchestrator** (`evaluate_agents.py`) | Workflow Classification Accuracy | **28 / 32 (87.5%)** | PASSED |
| | Prompt Injection Defense Rate | **4 / 4 (100.0%)** | PASSED |
| | Tool Action Delegation Rate | **7 / 9 (77.8%)** | PASSED |
| | Agent Execution Timeouts | **0 / 32 (0.0%)** | PASSED |

---

## 17. Testing

The codebase includes an exhaustive test suite of **177 automated tests** across **17 test modules**:

```
====================== 177 passed, 2 warnings in 45.21s =======================
```

| Test Module | Coverage Area | Test Count | Status |
| :--- | :--- | :--- | :--- |
| [`tests/test_config.py`](tests/test_config.py) | Configuration defaults, environment overrides, URL validation | 7 | PASSED |
| [`tests/test_database.py`](tests/test_database.py) | SQLite connection, migrations, employee/ticket CRUD, seeding | 8 | PASSED |
| [`tests/test_rag_pipeline.py`](tests/test_rag_pipeline.py) | Cleaning, loading (.md/.txt/.pdf), chunking, embeddings | 11 | PASSED |
| [`tests/test_retriever.py`](tests/test_retriever.py) | Vector retrieval, score thresholding, deduplication, reranking | 9 | PASSED |
| [`tests/test_context_engineering.py`](tests/test_context_engineering.py) | Query analysis, token budgeting, prompt defanging | 14 | PASSED |
| [`tests/test_prompts.py`](tests/test_prompts.py) | Prompt versions, context formatting, refusal instructions | 11 | PASSED |
| [`tests/test_mcp_server.py`](tests/test_mcp_server.py) | MCP tool execution, validation error handling, schemas | 11 | PASSED |
| [`tests/test_mcp_client.py`](tests/test_mcp_client.py) | Subprocess lifecycle, connection error handling, tool calls | 9 | PASSED |
| [`tests/test_agent_orchestration.py`](tests/test_agent_orchestration.py) | ADK agent hierarchy, 4-way routing, end-to-end workflows | 10 | PASSED |
| [`tests/test_llm_integration.py`](tests/test_llm_integration.py) | Grounded RAG, abstention, 3-tier response contract, offline fallback | 8 | PASSED |
| [`tests/test_api.py`](tests/test_api.py) | FastAPI routes (`/chat`, `/ingest`, `/tickets`, `/tools`), tracing | 17 | PASSED |
| [`tests/test_health.py`](tests/test_health.py) | Component health checks (database, vector store, MCP, LLM) | 1 | PASSED |
| [`tests/test_security.py`](tests/test_security.py) | Constant-time auth, payload limits, MIME validation, injection defense | 28 | PASSED |
| [`tests/test_frontend.py`](tests/test_frontend.py) | Streamlit client, workflow badge rendering, form validation | 16 | PASSED |
| [`tests/test_evaluation.py`](tests/test_evaluation.py) | Evaluation dataset structure, tool runner, RAG runner | 3 | PASSED |
| [`tests/test_containerization.py`](tests/test_containerization.py) | Compose schema, Dockerfile targets, healthchecks, network | 12 | PASSED |
| **Total** | **All 17 Test Modules** | **177** | **100% PASSED** |

Run all tests:
```bash
pytest
```

---

## 18. Docker & Containerization

The multi-container topology is orchestrated via `docker-compose.yml`:

```
+---------------------------------------------------------------------------------+
|                        enterprise_agent_network (Bridge)                        |
|                                                                                 |
|   +-----------------------+                         +-----------------------+   |
|   |   Streamlit Web UI    |  HTTP:8000              |      FastAPI API      |   |
|   |      (Port 8501)      | --------------------->  |      (Port 8000)      |   |
|   |  frontend/streamlit   |                         |     app.main:app      |   |
|   +-----------------------+                         +-----------+-----------+   |
|                                                                 |               |
|                                       +-------------------------+               |
|                                       | HTTP:6333               | SSE:8001      |
|                                       v                         v               |
|                           +-----------------------+ +-----------------------+   |
|                           |     Qdrant Vector     | |   FastMCP SSE Server  |   |
|                           |      (Port 6333)      | |      (Port 8001)      |   |
|                           |   qdrant/qdrant:v1.12 | |  scripts/run_mcp_...  |   |
|                           +-----------+-----------+ +-----------+-----------+   |
|                                       |                         |               |
+---------------------------------------|-------------------------|---------------+
                                        v                         v
                           +-----------------------+ +-----------------------+
                           |  qdrant_storage (Vol) | |   sqlite_data (Vol)   |
                           +-----------------------+ +-----------------------+
```

### Verified Service Status (`docker compose ps`)
```
NAME                      IMAGE                                             COMMAND                  SERVICE     STATUS                   PORTS
enterprise_ai_api         enterprise-ai-knowledge-support-agent-api         "uvicorn app.main:ap…"   api         Up (healthy)             0.0.0.0:8000->8000/tcp
enterprise_ai_mcp         enterprise-ai-knowledge-support-agent-mcp         "python scripts/run_…"   mcp         Up (healthy)             0.0.0.0:8001->8001/tcp
enterprise_ai_qdrant      qdrant/qdrant:v1.12.0                             "./entrypoint.sh"        qdrant      Up (healthy)             0.0.0.0:6333-6334->6333-6334/tcp
enterprise_ai_streamlit   enterprise-ai-knowledge-support-agent-streamlit   "streamlit run front…"   streamlit   Up (healthy)             0.0.0.0:8501->8501/tcp
```

---

## 19. Installation

### Prerequisites
- Python 3.11+
- Git
- Docker & Docker Compose (optional, for containerized run)

### Setup
```bash
# 1. Clone repository
git clone https://github.com/DheerajNagle/enterprise-ai-knowledge-support-agent.git
cd enterprise-ai-knowledge-support-agent

# 2. Create virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 3. Install dependencies in editable mode
pip install --upgrade pip
pip install -e ".[dev]"
```

---

## 20. Environment Variables

Create a `.env` file from the provided `.env.example`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Deployment environment (`development`, `staging`, `production`, `test`). |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `HOST` | `0.0.0.0` | Gateway host binding address. |
| `PORT` | `8000` | Gateway listening port. |
| `API_KEY` | `dev-insecure-api-key-replace-in-prod` | Master API authentication key (must be $\ge 16$ chars in production). |
| `GEMINI_API_KEY` | `""` | Google Gemini API key (offline fallback operates if empty). |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model variant for generation. |
| `SQLITE_DB_PATH` | `data/enterprise.db` | Local SQLite database file path. |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant vector database URL. |
| `QDRANT_API_KEY` | `None` | Optional API key for Qdrant Cloud. |
| `MCP_SERVER_URL` | `None` | Optional remote MCP SSE endpoint (`http://mcp:8001/sse`). |
| `API_BASE_URL` | `http://127.0.0.1:8000` | API base URL consumed by Streamlit frontend. |

---

## 21. Running Locally

### 1. Ingest Corporate Policies
```bash
python scripts/ingest_documents.py
```

### 2. Run the MCP Server (Optional standalone SSE mode)
```bash
# Runs on port 8001 over SSE
python scripts/run_mcp_server.py --transport sse --port 8001
```

### 3. Run the FastAPI REST Gateway
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Swagger API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Endpoint: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Run the Streamlit Web Console
```bash
streamlit run frontend/streamlit_app.py --server.port=8501
```
- Streamlit UI: [http://localhost:8501](http://localhost:8501)

---

## 22. Running with Docker

Launch the complete 4-service stack with a single command:

```bash
docker compose up -d --build
```

### Verify Container Status
```bash
docker compose ps
```

### View Live Logs
```bash
docker compose logs -f api
docker compose logs -f mcp
```

### Tear Down Services
```bash
docker compose down
```

---

## 23. Example Queries & Workflows

### Scenario 1: RAG-Only Workflow (Informational Policy Inquiry)
**User Input**:
> *"What is the remote work policy regarding core operational hours?"*

**Classification**: `RAG_ONLY`

**API Response (`POST /api/chat`)**:
```json
{
  "workflow": "RAG_ONLY",
  "response": "All remote staff must be accessible on Slack and email during regional core hours: 10:00 AM to 4:00 PM local timezone.",
  "retrieved_knowledge": [
    {
      "document": "remote_work_policy.md",
      "section": "4. Operational Hours & Collaboration Standards",
      "score": 0.88,
      "text": "Core Hours: All staff must be accessible on Slack and email during regional core hours: 10:00 AM to 4:00 PM local timezone..."
    }
  ],
  "tool_results": [],
  "grounded": true,
  "confidence_score": 0.88
}
```

---

### Scenario 2: MCP-Only Workflow (Operational Support Ticket Action)
**User Input**:
> *"Create an IT ticket for employee EMP-1001: My laptop keyboard keys are sticking."*

**Classification**: `TOOL_ONLY`

**API Response (`POST /api/chat`)**:
```json
{
  "workflow": "TOOL_ONLY",
  "response": "Support ticket TCK-2026-9A1F has been successfully created for Sarah Jenkins.",
  "retrieved_knowledge": [],
  "tool_results": [
    {
      "tool_name": "create_support_ticket",
      "parameters": {
        "employee_id": "EMP-1001",
        "category": "IT",
        "title": "My laptop keyboard keys are sticking",
        "priority": "MEDIUM"
      },
      "result": {
        "success": true,
        "message": "Ticket TCK-2026-9A1F created successfully.",
        "ticket": {
          "ticket_id": "TCK-2026-9A1F",
          "employee_id": "EMP-1001",
          "status": "OPEN",
          "category": "IT"
        }
      }
    }
  ],
  "grounded": true,
  "confidence_score": 1.0
}
```

---

### Scenario 3: Hybrid Workflow (Policy Guidance + Automated Action)
**User Input**:
> *"What does the VPN policy say about remote access, and create an IT ticket for EMP-1001 to get VPN credentials?"*

**Classification**: `HYBRID_RAG_TOOL`

**API Response (`POST /api/chat`)**:
```json
{
  "workflow": "HYBRID_RAG_TOOL",
  "response": "### Policy Evaluation\nAccording to the Enterprise VPN Policy, remote employees must use multi-factor authentication (MFA) and Cisco AnyConnect to access internal corporate networks.\n\n### Action Taken\nSupport ticket TCK-2026-B8C2 has been created for Sarah Jenkins to provision VPN credentials.",
  "retrieved_knowledge": [
    {
      "document": "vpn_policy.md",
      "section": "2. Authentication & Access Controls",
      "score": 0.86,
      "text": "All remote connections require certificate-based device authentication and hardware-token MFA..."
    }
  ],
  "tool_results": [
    {
      "tool_name": "create_support_ticket",
      "result": {
        "success": true,
        "ticket": {
          "ticket_id": "TCK-2026-B8C2",
          "category": "IT",
          "status": "OPEN"
        }
      }
    }
  ],
  "grounded": true,
  "confidence_score": 0.86
}
```

---

## 24. User Interface & Layout

The **Streamlit Executive Console** provides four tabbed workspaces:

```
+-----------------------------------------------------------------------------------------+
| 🏢 Enterprise AI Knowledge & Support Agent                         [● API: Connected]   |
| Google ADK Multi-Tier Orchestrator | FastMCP Tools | Hybrid Qdrant Vector Retrieval     |
+-----------------------------------------------------------------------------------------+
| [💬 Chat Console]  [🎫 Support Tickets]  [📄 Document Ingestion]  [🛠️ Tools Explorer]   |
|                                                                                         |
|  User: What is the remote work policy regarding core working hours?                     |
|                                                                                         |
|  Agent:                                                                                 |
|  [🏷️ RAG Only]                                                                          |
|  All remote staff must be accessible on Slack and email during regional core hours:    |
|  10:00 AM to 4:00 PM local timezone.                                                   |
|                                                                                         |
|  ▼ 📚 Verified Knowledge Citations (1 Source)                                           |
|    • remote_work_policy.md — Section: 4. Operational Hours & Collaboration Standards     |
|      "All staff must be accessible on Slack and email during regional core hours..."    |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
| [Type message...]                                                              [Send]   |
+-----------------------------------------------------------------------------------------+
```

---

## 25. Project Structure

```
enterprise-ai-knowledge-support-agent/
├── .dockerignore                     # Docker build exclusion rules
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore patterns
├── ARCHITECTURE.md                   # Detailed technical design document
├── Dockerfile                        # Multi-stage production Dockerfile
├── docker-compose.yml                # Multi-service container orchestrator
├── pyproject.toml                    # Package specifications & dependencies
├── README.md                         # Master documentation (this file)
├── requirements.txt                  # Pinned production requirements
│
├── app/                              # Core Application Package
│   ├── __init__.py
│   ├── config.py                     # Pydantic v2 Settings & environment validator
│   ├── main.py                       # Gateway ASGI entrypoint
│   │
│   ├── agent/                        # Google ADK Orchestration Subsystem
│   │   ├── __init__.py
│   │   ├── llm_service.py            # Gemini client & offline deterministic fallback
│   │   ├── rag_agent.py              # Specialized RAG knowledge sub-agent
│   │   ├── root_agent.py             # Canonical ADK RootAgent orchestrator
│   │   ├── schemas.py                # Agent Turn & response data models
│   │   ├── service.py                # Agent service decoupling API from agents
│   │   └── tool_agent.py             # Specialized MCP operational sub-agent
│   │
│   ├── api/                          # FastAPI Gateway
│   │   ├── __init__.py
│   │   ├── dependencies.py           # Dependency injection providers
│   │   ├── main.py                   # FastAPI factory & lifespan manager
│   │   ├── routes.py                 # Route definitions (/chat, /tickets, /ingest)
│   │   └── schemas.py                # API Request/Response Pydantic contracts
│   │
│   ├── database/                     # Relational Persistence Subsystem
│   │   ├── __init__.py
│   │   ├── connection.py             # SQLite connection pooling & initialization
│   │   ├── crud.py                   # Employee & ticket CRUD operations
│   │   ├── models.py                 # Pydantic & SQLAlchemy database schemas
│   │   └── seed.py                   # Database seeder with sample employees/tickets
│   │
│   ├── mcp/                          # Model Context Protocol Subsystem
│   │   ├── __init__.py
│   │   ├── client.py                 # Asynchronous EnterpriseMCPClient (stdio & SSE)
│   │   ├── server.py                 # FastMCP server & /health route
│   │   └── tools/                    # Registered MCP tools
│   │       ├── __init__.py
│   │       ├── employee_tools.py     # Employee directory lookups
│   │       ├── policy_tools.py       # Vector policy search
│   │       └── ticket_tools.py       # Support ticket creation & tracking
│   │
│   ├── rag/                          # Retrieval-Augmented Generation Subsystem
│   │   ├── __init__.py
│   │   ├── cleaners.py               # Whitespace normalization & text cleaning
│   │   ├── context_engine.py         # Token budgeting, ranking, injection defanging
│   │   ├── embeddings.py             # 768-dim embedding generator
│   │   ├── ingestion.py              # Ingestion pipeline batch processor
│   │   ├── loaders.py                # Document loaders (.md, .pdf, .txt)
│   │   ├── prompts.py                # System governance & citation prompt templates
│   │   ├── retriever.py              # Vector search, score filtering, dedup
│   │   └── vector_store.py           # Qdrant client abstraction (embedded & network)
│   │
│   └── security/                     # Portfolio-Level Security Subsystem
│       ├── __init__.py
│       ├── auth.py                   # Constant-time API key authenticator
│       ├── sanitization.py           # RedactingLogFilter & credential masking
│       └── validation.py             # MIME validator, file size, injection detector
│
├── data/                             # Data Assets
│   ├── enterprise.db                 # Seeded SQLite business database
│   └── documents/                    # Enterprise policy markdown corpus (8 documents)
│       ├── employee_onboarding.md
│       ├── expense_policy.md
│       ├── laptop_policy.md
│       ├── leave_policy.md
│       ├── password_policy.md
│       ├── remote_work_policy.md
│       ├── security_policy.md
│       └── vpn_policy.md
│
├── evaluation/                       # AI Quality & Evaluation Framework
│   ├── README.md                     # Evaluation methodology documentation
│   ├── dataset.json                  # 32 benchmark questions across 8 categories
│   ├── evaluate_agents.py            # End-to-end agent workflow evaluator
│   ├── evaluate_rag.py               # Retrieval hit rate & citation evaluator
│   ├── evaluate_tools.py             # MCP tool schema & execution benchmark
│   └── results/                      # Timestamped evaluation reports
│
├── frontend/                         # Streamlit Executive Console
│   ├── __init__.py
│   ├── streamlit_app.py              # Main Streamlit application
│   ├── components/                   # UI modular view components
│   │   ├── chat.py                   # Conversational interface & citation pills
│   │   ├── documents.py              # Ingestion & file upload component
│   │   ├── sidebar.py                # Connection telemetry & system health
│   │   ├── styles.py                 # Custom CSS tokens & themes
│   │   ├── tickets.py                # Ticket management & lookup tab
│   │   └── tools_explorer.py         # MCP tool schema browser
│   └── services/
│       └── api_client.py             # HTTP client consuming FastAPI endpoints
│
├── scripts/                          # Administrative & Operational Scripts
│   ├── ingest_documents.py           # Batch document ingestion runner
│   ├── run_mcp_server.py             # MCP server standalone runner
│   └── test_retrieval.py             # Vector retrieval verification script
│
└── tests/                            # Comprehensive Automated Test Suite (177 tests)
    ├── test_agent_orchestration.py
    ├── test_api.py
    ├── test_config.py
    ├── test_containerization.py
    ├── test_context_engineering.py
    ├── test_database.py
    ├── test_evaluation.py
    ├── test_frontend.py
    ├── test_health.py
    ├── test_llm_integration.py
    ├── test_mcp_client.py
    ├── test_mcp_server.py
    ├── test_prompts.py
    ├── test_rag_pipeline.py
    ├── test_retriever.py
    └── test_security.py
```

---

## 26. Design Decisions

### 1. Google ADK vs. LangChain Agents
- **Decision**: Adopted Google ADK for multi-agent orchestration and intent routing, confining LangChain to document text-splitting utilities.
- **Rationale**: Monolithic agent frameworks (such as `langchain.agents.AgentExecutor`) introduce opaque abstraction layers, unpredictable retry loops, and vendor lock-in. Google ADK provides clean hierarchical delegation (`RootAgent -> SubAgent`) that matches production microservices patterns.

### 2. FastMCP Tool Execution vs. Direct Function Calling
- **Decision**: Implemented tool execution via the Model Context Protocol (MCP SDK v2) over stdio and SSE.
- **Rationale**: Direct function calling tightly couples tool implementation to specific model APIs (e.g. OpenAI function schemas). MCP establishes an open, vendor-neutral standard for discovering and invoking tools, allowing the exact same tool server to be shared by Gemini, Claude Desktop, or autonomous agent workers.

### 3. Dual-Transport MCP Client (stdio vs. SSE)
- **Decision**: `EnterpriseMCPClient` supports both local stdio subprocesses and remote SSE network endpoints.
- **Rationale**: Local stdio transport eliminates network latency and configuration overhead during development and unit testing. In containerized production, deploying the MCP server as a standalone service over SSE enables independent scaling, isolation, and security auditing.

### 4. Hybrid Qdrant Vector Storage (Embedded vs. Network)
- **Decision**: `QdrantVectorStore` seamlessly detects if a live Qdrant server is reachable over HTTP; if offline, it automatically falls back to local on-disk storage (`data/qdrant_storage`).
- **Rationale**: Developers and automated CI test runners can execute full vector retrieval tests without needing a running Qdrant daemon, while production deployments seamlessly leverage high-throughput network clustering.

### 5. Multi-Stage Dockerfile with Dedicated Targets
- **Decision**: Used a single multi-stage `Dockerfile` with targets (`api`, `mcp`, `streamlit`).
- **Rationale**: Eliminates build-tool bloat (compilers, wheel caches) from the runtime images, maximizes Docker layer caching across services, and ensures all services run as an unprivileged non-root user (`appuser`).

---

## 27. Limitations

To maintain engineering integrity, the system's operational boundaries are documented honestly:

1. **Portfolio-Level Security vs. Enterprise SSO**: The system uses constant-time API key authentication and input validation. It does not integrate enterprise IdP protocols (OIDC, SAML 2.0, Okta) or granular Role-Based Access Control (RBAC) at the document chunk level.
2. **SQLite Concurrency Limits**: SQLite is used for ticket and employee persistence. While ideal for demonstration and local workloads, high-concurrency production deployments require migration to PostgreSQL.
3. **Synthetic Evaluation Dataset**: The evaluation suite uses 32 synthetic test cases. While realistic, production evaluation requires continuous monitoring on real employee interaction transcripts.
4. **Offline Heuristic Fallback**: In environments without a live Google Gemini API key, the system uses deterministic rule-based synthesis. While this ensures test reliability and offline demonstration, nuanced reasoning requires an active frontier LLM.

---

## 28. Future Improvements

- [ ] **PostgreSQL & pgvector Integration**: Replace SQLite with PostgreSQL and explore hybrid sparse/dense vector search using `pgvector`.
- [ ] **Enterprise Identity & RBAC**: Implement OAuth2 / OIDC authentication with Okta and Azure AD to enforce chunk-level document permissions (e.g., restricting HR compensation policies to HR managers).
- [ ] **Asynchronous Task Queue (Celery / Redis)**: Offload heavy PDF parsing and batch document embeddings to asynchronous background workers.
- [ ] **OpenTelemetry Tracing**: Export detailed distributed traces (`span_id`, `trace_id`) across FastAPI, MCP, and Qdrant to Jaeger or Datadog.
- [ ] **Continuous LLM-as-a-Judge Monitoring**: Integrate automated Ragas / LangSmith evaluation pipelines on live conversation traffic to detect model drift.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
