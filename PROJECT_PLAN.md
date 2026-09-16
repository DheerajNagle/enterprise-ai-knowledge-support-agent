# Enterprise AI Knowledge & Support Agent
## Master Implementation Project Plan

---

## Overview

This project plan details the step-by-step engineering roadmap for implementing the **Enterprise AI Knowledge & Support Agent**. The roadmap is divided into 10 cohesive, test-driven phases. Each phase establishes clean contracts, utilizes non-deprecated modern APIs, and includes verification criteria before moving to subsequent phases.

---

## Phase 1: Foundation, Dependency Architecture & Environment Setup

### 1. Objective
Establish the project environment, package management, developer toolchains (linting, formatting, type checking), and modern dependencies with strict version pinning for Python 3.11+.

### 2. Files to Create
- `pyproject.toml`: Modern Python project specification with dependencies, Ruff, Black, and Pytest configs.
- `requirements.txt`: Pinned production dependencies.
- `requirements-dev.txt`: Development dependencies (Pytest, Ruff, Mypy, Pre-commit).
- `.env.example`: Comprehensive environment variable template with all configuration keys.
- `README.md`: Updated portfolio overview, architectural highlights, and local quickstart instructions.

### 3. Dependencies
```text
python >= 3.11
google-adk >= 0.1.0
google-genai >= 0.1.0
langchain >= 0.3.0
langchain-core >= 0.3.0
langchain-community >= 0.3.0
langchain-google-genai >= 2.0.0
langchain-qdrant >= 0.2.0
qdrant-client >= 1.12.0
mcp >= 1.3.0
fastapi >= 0.115.0
uvicorn[standard] >= 0.32.0
pydantic >= 2.9.0
pydantic-settings >= 2.6.0
streamlit >= 1.40.0
ragas >= 0.2.0
pytest >= 8.3.0
pytest-asyncio >= 0.24.0
httpx >= 0.27.0
rich >= 13.9.0
```

### 4. Implementation Tasks
1. Configure `pyproject.toml` specifying project metadata, Python version constraint `>=3.11`, Ruff linter rules, and Pytest async configuration.
2. Build `requirements.txt` and `requirements-dev.txt` isolating runtime and test tools.
3. Validate virtual environment creation and dependency resolution without conflicts.
4. Establish `.env.example` documenting Google GenAI API keys, Qdrant cluster endpoints, MCP configuration, and security tokens.

### 5. Testing Requirements
- Execute `python --version` verifying Python 3.11+.
- Execute `pip check` ensuring no conflicting dependency constraints.
- Run `pytest --version` and `ruff --version` verifying developer tooling readiness.

### 6. Expected Result
A clean, fully resolved Python 3.11+ environment with locked dependencies and modern tooling ready for core development.

---

## Phase 2: Configuration, Structured Logging & Pydantic v2 Core Schemas

### 2.1 Objective
Build a strongly typed configuration system, structured JSON logging with correlation IDs, and unified Pydantic v2 data models for requests, responses, citations, documents, and agent states.

### 2.2 Files to Create
- `src/core/config.py`: Pydantic-settings `Settings` class with environment validation.
- `src/core/logging.py`: Structured JSON logger with contextual trace IDs (`structlog` or `logging.Formatter`).
- `src/schemas/query.py`: `QueryRequest`, `QueryResponse`, `Citation`, `ExecutionTrace`.
- `src/schemas/document.py`: `DocumentMetadata`, `IngestionRequest`, `IngestionResponse`, `DocumentChunk`.
- `src/schemas/agent.py`: `AgentState`, `AgentIntent`, `ToolCallRecord`, `ResolutionStatus`.
- `tests/unit/test_config.py`: Unit tests for config defaults and environment overrides.
- `tests/unit/test_schemas.py`: Unit tests for Pydantic v2 schema validation.

### 2.3 Dependencies
- `pydantic >= 2.9.0`
- `pydantic-settings >= 2.6.0`
- `pytest >= 8.3.0`

### 2.4 Implementation Tasks
1. Implement `Settings` in `src/core/config.py` validating `GEMINI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `API_AUTH_KEY`, and embedding dimensions.
2. Implement custom JSON log formatter in `src/core/logging.py` injecting `timestamp`, `level`, `trace_id`, `module`, and `message`.
3. Construct Pydantic v2 schemas in `src/schemas/` with field validations, regex constraints, and default examples for Swagger documentation.

### 2.5 Testing Requirements
- Test `test_config.py`: Confirm missing required environment variables raise `ValidationError` when not provided with fallback defaults.
- Test `test_schemas.py`: Validate string length constraints on queries, valid citation structure, and serialization round-trips.

### 2.6 Expected Result
Strongly typed runtime configuration and strict data validation layers serving as the single source of truth for the entire application.

---

## Phase 3: Knowledge Ingestion & Vector Storage Pipeline (Qdrant & Embeddings)

### 3.1 Objective
Implement document parsing, semantic chunking, embedding generation using Google Gemini (`text-embedding-004`), and high-performance vector storage and indexing with Qdrant.

### 3.2 Files to Create
- `src/knowledge/loader.py`: Text, Markdown, and PDF document parser with text sanitization.
- `src/knowledge/chunker.py`: Recursive character and semantic chunker with token overlap and metadata preservation.
- `src/knowledge/embeddings.py`: Embedding adapter utilizing `GoogleGenerativeAIEmbeddings` / `google-genai`.
- `src/knowledge/vector_store.py`: Qdrant collection manager and `QdrantVectorStore` client wrapper.
- `src/knowledge/ingest.py`: End-to-end ingestion pipeline with batch upsert and payload indexing.
- `tests/unit/test_chunker.py`: Unit tests for chunk size, overlap, and metadata attribution.
- `tests/integration/test_vector_store.py`: Integration tests for Qdrant in-memory vector storage and payload filtering.

### 3.3 Dependencies
- `qdrant-client >= 1.12.0`
- `langchain-qdrant >= 0.2.0`
- `langchain-google-genai >= 2.0.0`
- `pypdf >= 5.0.0`
- `tiktoken >= 0.8.0`

### 3.4 Implementation Tasks
1. Implement `DocumentLoader` supporting Markdown, PDF, and TXT files, extracting title, department, and timestamps.
2. Build `SemanticChunker` enforcing an 800-token maximum with 150-token sliding window overlap, stamping each chunk with unique IDs (`doc_id:chunk_n`).
3. Create `EmbeddingManager` to interface with Google's `text-embedding-004` (768 dimensions), including rate limit backoff and batching.
4. Implement `QdrantManager` managing collections, HNSW vector indexing, and payload schemas (department, access_role, doc_id).
5. Add in-memory support (`:memory:`) in `QdrantManager` for unit/integration testing without requiring a live external Qdrant instance.

### 3.5 Testing Requirements
- Test chunking logic with diverse document sizes; ensure no tokens are dropped and overlap metadata is preserved.
- Run `test_vector_store.py` against `QdrantClient(":memory:")` asserting successful upsert, cosine search, and department payload filtering.

### 3.6 Expected Result
A robust ingestion engine capable of chunking enterprise documents, calculating vector embeddings, and indexing them into Qdrant collections with rich queryable metadata.

---

## Phase 4: Context Engineering, Prompt Engineering & Advanced RAG Engine

### 4.1 Objective
Build the context engineering pipeline that calculates token budgets, formats conversation memory, constructs strictly grounded system prompts, filters low-confidence context, and assembles verifiable citations.

### 4.2 Files to Create
- `src/rag/budgeter.py`: Token budgeter calculating dynamic allocations for system prompt, context chunks, memory, and output.
- `src/rag/memory.py`: Sliding window conversation memory with metadata tracking and truncation.
- `src/rag/retriever.py`: Hybrid retriever querying Qdrant with similarity thresholds and role-based filtering.
- `src/rag/prompts.py`: Production prompt templates (System Grounding Prompt, Citation Instruction, Abstention Prompt).
- `src/rag/engine.py`: Core RAG orchestrator assembling context and invoking the Gemini generation pipeline.
- `tests/unit/test_budgeter.py`: Unit tests for token budgeting and graceful truncation.
- `tests/unit/test_rag_engine.py`: Unit tests for similarity filtering, citation parsing, and prompt assembly.

### 4.3 Dependencies
- `langchain-core >= 0.3.0`
- `langchain-google-genai >= 2.0.0`
- `tiktoken >= 0.8.0`

### 4.4 Implementation Tasks
1. Implement `TokenBudgeter` that enforces token ceiling (e.g., 4000 tokens for retrieval context) and prunes lower-ranked chunks.
2. Build `ConversationMemory` managing chat turns with role tags (`user`, `assistant`, `system`), preserving recent history within budget.
3. Build `GroundedRetriever` wrapping Qdrant with:
   - Minimum similarity threshold cutoff ($score \ge 0.72$).
   - Extraction of citation references (`document_id`, `source_name`, `page_number`).
4. Develop prompt templates in `prompts.py` requiring the LLM to output structured answers with brackets `[Source: DOC_ID, Page: N]`.
5. Implement fallback logic: If no retrieved chunks meet the threshold, trigger the abstention protocol immediately.

### 4.5 Testing Requirements
- Unit test `TokenBudgeter` with oversized context; verify chunks are dropped from lowest score up until budget fits.
- Test `GroundedRetriever` with mocked Qdrant results above and below $0.72$ threshold; assert below-threshold items are omitted.
- Test citation parser extracting clean citation lists from formatted model text.

### 4.6 Expected Result
A resilient RAG engine with strict context budgeting, high-precision retrieval, verifiable citations, and deterministic abstention on unknown queries.

---

## Phase 5: Model Context Protocol (MCP) Server & Client Subsystem

### 5.1 Objective
Implement Model Context Protocol (MCP) servers using the official `FastMCP` framework, and build an asynchronous MCP client using `ClientSession` to empower agents with standardized, isolated tools for ticketing and customer CRM.

### 5.2 Files to Create
- `src/mcp_servers/ticket_server.py`: FastMCP server exposing IT/Support ticketing tools.
- `src/mcp_servers/crm_server.py`: FastMCP server exposing customer/employee profile tools.
- `src/mcp_client/session_manager.py`: MCP client managing server sub-processes or HTTP connections via `ClientSession`.
- `src/mcp_client/tool_adapter.py`: Adapter converting MCP tools into callable agent tools.
- `tests/unit/test_mcp_servers.py`: Unit tests for FastMCP tool declarations and executions.
- `tests/integration/test_mcp_client.py`: Integration test connecting `ClientSession` via `stdio_client` and invoking tools.

### 5.3 Dependencies
- `mcp >= 1.3.0`
- `pydantic >= 2.9.0`
- `pytest-asyncio >= 0.24.0`

### 5.4 Implementation Tasks
1. Implement `ticket_server.py` using `FastMCP("TicketingService")`:
   - Tool `create_ticket(title: str, description: str, priority: str, department: str) -> dict`
   - Tool `get_ticket_status(ticket_id: str) -> dict`
   - Tool `escalate_ticket(ticket_id: str, reason: str) -> dict`
2. Implement `crm_server.py` using `FastMCP("CRMService")`:
   - Tool `get_customer_profile(email: str) -> dict`
   - Tool `check_service_tier(account_id: str) -> dict`
3. Build `MCPClientManager` using `mcp.client.stdio.stdio_client` and `mcp.ClientSession`:
   - Manage startup and shutdown lifecycles of MCP servers.
   - Dynamically discover tool schemas via `session.list_tools()`.
   - Safely execute tools via `session.call_tool(name, arguments)`.
4. Wrap MCP tools for native integration with Google ADK and LangChain agents.

### 5.5 Testing Requirements
- Unit test each MCP tool function directly with valid and invalid parameters.
- Integration test spawning the MCP server via `stdio_client`, listing tools via `ClientSession.list_tools()`, and executing `create_ticket`.

### 5.6 Expected Result
Standardized, decoupled MCP tool servers and client infrastructure providing secure enterprise tool execution via standard protocol.

---

## Phase 6: Google ADK & Multi-Agent Orchestration Engine

### 6.1 Objective
Construct the multi-agent system using Google Agent Development Kit (ADK) and Gemini LLM. Implement the Supervisor Agent that classifies intent, delegates tasks to specialized sub-agents (Knowledge Agent, Support Action Agent, Guardrail Agent), and synthesizes validated answers.

### 6.2 Files to Create
- `src/agents/supervisor.py`: Primary supervisor agent orchestrating routing and synthesis.
- `src/agents/knowledge_agent.py`: Specialized agent for factual RAG retrieval.
- `src/agents/support_agent.py`: Specialized agent interacting with MCP ticketing/CRM tools.
- `src/agents/guardrail_agent.py`: Safety agent scanning inputs/outputs for PII, prompt injections, and grounding.
- `src/agents/orchestrator.py`: Unified interface linking all agents, sessions, and memory.
- `tests/unit/test_agents.py`: Unit tests for intent classification and delegation rules.
- `tests/integration/test_orchestrator.py`: Multi-turn integration tests with mocked tool calls.

### 6.3 Dependencies
- `google-adk >= 0.1.0`
- `google-genai >= 0.1.0`
- `langchain >= 0.3.0`
- `langchain-google-genai >= 2.0.0`

### 6.4 Implementation Tasks
1. Define agent personas, instructions, and tool sets:
   - `KnowledgeAgent`: Armed with Qdrant retrieval tools and citation constraints.
   - `SupportActionAgent`: Armed with MCP ticketing tools.
   - `GuardrailAgent`: Deterministic regex + heuristic checks for PII (SSN, credit card) and prompt injection phrases.
2. Implement `SupervisorAgent` utilizing Google ADK `Agent` abstraction:
   - Evaluates incoming query intent: `KNOWLEDGE_INQUIRY`, `ACTION_REQUEST`, `HYBRID`, or `OUT_OF_SCOPE`.
   - Delegates sub-tasks to respective agents.
3. Build `AgentOrchestrator` to manage end-to-end flow:
   - Ingests user input $\rightarrow$ Guardrail pre-check $\rightarrow$ Supervisor delegation $\rightarrow$ Synthesis $\rightarrow$ Guardrail post-check $\rightarrow$ Structured response.
4. Implement fallback handling: If a tool fails or sub-agent errors, provide graceful degradation with clear user feedback.

### 6.5 Testing Requirements
- Unit test intent routing: Verify "What is our vacation policy?" routes to `KnowledgeAgent`; "Create ticket for broken mouse" routes to `SupportActionAgent`.
- Test `GuardrailAgent` detecting injected strings (e.g. "Ignore previous instructions") and masking PII.
- Test end-to-end orchestration returning valid `QueryResponse` schemas.

### 6.6 Expected Result
A fully functional hierarchical multi-agent system built on Google ADK capable of coordinated retrieval, action execution, and safety evaluation.

---

## Phase 7: Enterprise FastAPI REST Gateway & Security Layer

### 7.1 Objective
Develop a production-grade FastAPI REST API with API key authentication, correlation IDs, rate limiting, request validation, structured error handling, and comprehensive OpenAPI documentation.

### 7.2 Files to Create
- `src/api/main.py`: FastAPI application factory with lifespan management.
- `src/api/security.py`: API key / Bearer token security dependencies and scope verification.
- `src/api/middleware.py`: Request correlation ID injection, execution timing, and error logging middleware.
- `src/api/routes/query.py`: `/api/v1/query` and `/api/v1/chat` endpoints.
- `src/api/routes/documents.py`: Ingestion, document listing, and deletion endpoints.
- `src/api/routes/mcp_tools.py`: MCP tool status and registry inspection endpoints.
- `src/api/routes/health.py`: Liveness, readiness, and system telemetry endpoints.
- `tests/integration/test_api.py`: FastAPI endpoint tests using `httpx.AsyncClient`.

### 7.3 Dependencies
- `fastapi >= 0.115.0`
- `uvicorn[standard] >= 0.32.0`
- `httpx >= 0.27.0`
- `python-multipart >= 0.0.12`

### 7.4 Implementation Tasks
1. Configure FastAPI app with metadata, OpenAPI documentation tags, and CORS middleware.
2. Implement `APIKeyHeader` authentication in `src/api/security.py` checking keys against environment configurations.
3. Add custom middleware injecting `X-Correlation-ID` into request/response headers and logging elapsed time in milliseconds.
4. Build `/api/v1/query` and `/api/v1/chat` handlers invoking `AgentOrchestrator` and returning validated `QueryResponse`.
5. Implement `/api/v1/documents/ingest` accepting file uploads (`.pdf`, `.md`, `.txt`) and routing to the ingestion pipeline.
6. Implement RFC 7807 standard exception handlers for `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, and `500 Internal Error`.

### 7.5 Testing Requirements
- Test `/health` returns status `200 OK` with system component health.
- Test `/api/v1/query` without `X-API-Key` returns `401 Unauthorized`.
- Test `/api/v1/query` with valid key and query returns `200 OK` matching `QueryResponse` schema.
- Test `/api/v1/documents/ingest` with invalid file type returns `422 Unprocessable Entity`.

### 7.6 Expected Result
A hardened, secure, self-documenting REST API gateway acting as the enterprise entrypoint for all agent operations.

---

## Phase 8: Streamlit Production Support Console & Citations UI

### 8.1 Objective
Construct an intuitive, modern Streamlit frontend for interacting with the Knowledge & Support Agent, inspecting source citations, reviewing execution traces, uploading documents, and monitoring system health.

### 8.2 Files to Create
- `streamlit_app/app.py`: Main Streamlit application entrypoint with sidebar navigation.
- `streamlit_app/views/chat_view.py`: Conversational chat console with message history and citation expanders.
- `streamlit_app/views/document_view.py`: Document ingestion portal with file uploader and index stats.
- `streamlit_app/views/mcp_view.py`: MCP tool explorer and manual execution tester.
- `streamlit_app/views/telemetry_view.py`: Latency, confidence score, and token usage dashboards.
- `streamlit_app/components/citation_card.py`: Component rendering clickable source badges and context snippets.
- `streamlit_app/api_client.py`: Typed HTTP client communicating with the FastAPI backend.

### 8.3 Dependencies
- `streamlit >= 1.40.0`
- `httpx >= 0.27.0`
- `pandas >= 2.2.0`

### 8.4 Implementation Tasks
1. Build `APIClient` in `streamlit_app/api_client.py` wrapping calls to the FastAPI backend with error handling and retry logic.
2. Create `chat_view.py` using `st.chat_message` and `st.chat_input`:
   - Renders bot messages with collapsible citations (`[Doc ID, Page]`).
   - Displays confidence metrics and response generation time badges.
3. Build `document_view.py` allowing users to upload enterprise policy files and view indexed collection counts in Qdrant.
4. Build `mcp_view.py` listing connected MCP servers and available tools with live status indicators.
5. Apply professional dark/light theme styling with responsive layout.

### 8.5 Testing Requirements
- Manual verification of UI responsiveness: Start FastAPI backend and launch `streamlit run streamlit_app/app.py`.
- Verify chat message submission returns answers with expandable citation components.
- Verify document file upload triggers ingestion API and refreshes collection statistics.

### 8.6 Expected Result
A clean, production-ready enterprise console delivering real-time agent conversations, transparent citations, and document management.

---

## Phase 9: AI Evaluation & Automated Quality Harness (Ragas / LLM-as-a-Judge)

### 9.1 Objective
Establish an automated evaluation framework to benchmark and continuously monitor RAG output quality, faithfulness (absence of hallucination), context precision, and answer relevancy using synthetic ground-truth datasets.

### 9.2 Files to Create
- `eval/dataset.json`: Golden benchmark dataset with 20+ enterprise questions, contexts, and ground-truth answers.
- `eval/evaluator.py`: Evaluation pipeline executing questions through the agent and computing metrics.
- `eval/metrics.py`: Metric implementations (Faithfulness, Answer Relevancy, Context Precision).
- `tests/eval/test_rag_quality.py`: Automated Pytest suite asserting quality thresholds.
- `scripts/run_eval.py`: CLI script generating evaluation reports and summary tables.

### 9.3 Dependencies
- `ragas >= 0.2.0`
- `langchain-google-genai >= 2.0.0`
- `tabulate >= 0.9.0`
- `pytest >= 8.3.0`

### 9.4 Implementation Tasks
1. Construct `eval/dataset.json` covering IT policies, HR guidelines, technical setups, and adversarial ungrounded questions.
2. Build evaluation harness in `eval/evaluator.py` querying the RAG pipeline for each question.
3. Compute core evaluation metrics:
   - **Faithfulness**: Proportion of claims in the answer that can be directly verified in the retrieved context.
   - **Answer Relevance**: Measure of how directly the generated answer satisfies the original user question.
   - **Context Recall**: Measure of whether the retrieved context contains all necessary facts present in the ground truth.
4. Implement `test_rag_quality.py` asserting minimum score thresholds:
   - Average Faithfulness $\ge 0.85$
   - Average Answer Relevance $\ge 0.85$
5. Output detailed markdown evaluation report with pass/fail breakdown.

### 9.5 Testing Requirements
- Execute `python scripts/run_eval.py` asserting successful computation across all evaluation questions.
- Execute `pytest tests/eval/test_rag_quality.py` verifying automated test assertion passes.

### 9.6 Expected Result
An objective, automated AI evaluation framework providing measurable quality guarantees against hallucinations and retrieval failures.

---

## Phase 10: Dockerization, Container Networking & Production Verification

### 10.1 Objective
Containerize all components into isolated microservices using multi-stage Docker builds and Docker Compose, validating complete system boot, network isolation, and production readiness.

### 10.2 Files to Create
- `Dockerfile.api`: Multi-stage Dockerfile for FastAPI backend with non-root security user.
- `Dockerfile.ui`: Multi-stage Dockerfile for Streamlit frontend.
- `docker-compose.yml`: Multi-container topology (FastAPI, Streamlit, Qdrant, volume mounts, healthchecks).
- `.dockerignore`: Exclude cache, virtualenvs, secrets, and git files.
- `scripts/verify_deployment.sh` / `scripts/verify_deployment.ps1`: Automated healthcheck and smoke test script.

### 10.3 Dependencies
- Docker Engine 24.0+
- Docker Compose v2+

### 10.4 Implementation Tasks
1. Author `Dockerfile.api`:
   - Stage 1 (builder): Install build tools and wheel compilation.
   - Stage 2 (runtime): Python 3.11-slim base, copy wheels, create non-root `appuser`, expose port 8000, add healthcheck.
2. Author `Dockerfile.ui`:
   - Streamlit runtime, non-root user, expose port 8501, configure backend URL environment variable.
3. Construct `docker-compose.yml`:
   - Service `qdrant`: Image `qdrant/qdrant:v1.12.0`, ports `6333:6333`, volume `qdrant_data:/qdrant/storage`.
   - Service `api`: Depends on `qdrant` (condition: service_healthy), environment file `.env`, port `8000:8000`.
   - Service `ui`: Depends on `api` (condition: service_healthy), port `8501:8501`.
   - Dedicated bridge network `enterprise-agent-net`.
4. Implement automated verification script testing:
   - Qdrant cluster readiness (`GET http://localhost:6333/readyz`).
   - FastAPI gateway health (`GET http://localhost:8000/health`).
   - Sample RAG query execution via curl (`POST http://localhost:8000/api/v1/query`).
   - Streamlit UI HTTP status (`GET http://localhost:8501`).

### 10.5 Testing Requirements
- Run `docker compose build` verifying clean multi-stage build without layer errors.
- Run `docker compose up -d` verifying all containers report healthy status.
- Execute `scripts/verify_deployment.ps1` verifying all endpoints respond successfully inside containers.

### 10.6 Expected Result
A fully containerized, production-grade microservices deployment capable of running anywhere with a single `docker compose up` command.

---

## Phase Execution Summary Matrix

| Phase | Core Focus | Key Technologies | Primary Deliverables |
|---|---|---|---|
| **Phase 1** | Scaffolding & Setup | Python 3.11, Pip, Ruff, Pytest | `pyproject.toml`, `requirements.txt`, `.env.example` |
| **Phase 2** | Config & Schemas | Pydantic v2, Pydantic-Settings, Structlog | `Settings`, `QueryRequest/Response`, `Citation` |
| **Phase 3** | Ingestion & Storage | Qdrant, Google Embeddings, LangChain | `DocumentLoader`, `SemanticChunker`, `QdrantManager` |
| **Phase 4** | Context & RAG Engine | Context Engineering, Gemini, LangChain | `TokenBudgeter`, `GroundedRetriever`, `RAGEngine` |
| **Phase 5** | MCP Subsystem | Model Context Protocol, FastMCP, ClientSession | `ticket_server.py`, `crm_server.py`, `MCPClient` |
| **Phase 6** | Agent Orchestration | Google ADK, Gemini, LangChain | `SupervisorAgent`, `KnowledgeAgent`, `SupportAgent` |
| **Phase 7** | REST Gateway | FastAPI, Uvicorn, API Auth, Middleware | `/api/v1/query`, `/api/v1/documents`, Auth Middleware |
| **Phase 8** | Web Interface | Streamlit, Requests, Custom Components | Chat Console, Citation Viewer, Ingestion Portal |
| **Phase 9** | AI Evaluation | Ragas, Ground Truth Benchmark, Pytest | `dataset.json`, Faithfulness/Recall Metrics, Pytest suite |
| **Phase 10** | Production Deployment | Docker, Docker Compose, Multi-stage builds | `Dockerfile.api`, `Dockerfile.ui`, `docker-compose.yml` |
