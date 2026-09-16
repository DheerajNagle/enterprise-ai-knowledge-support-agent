# Enterprise AI Knowledge & Support Agent
## System Architecture Specification

---

## 1. Executive Summary & Architectural Vision

The **Enterprise AI Knowledge & Support Agent** is a production-grade, multi-agent enterprise platform designed to resolve complex employee and customer inquiries with high factual accuracy, verifiable citations, and real-time system actions.

The architecture combines:
- **Google Agent Development Kit (ADK)** for deterministic and hierarchical agent orchestration.
- **Gemini 2.5 / 1.5 Series LLMs** via official Google GenAI and LangChain integrations for reasoning and high-context comprehension.
- **Retrieval-Augmented Generation (RAG)** backed by **Qdrant Vector Database** featuring hybrid search (dense embeddings + payload filtering) and citation tracking.
- **Model Context Protocol (MCP)** via the official MCP Python SDK (`FastMCP` and `ClientSession`) to establish isolated, secure tool calling for internal enterprise backends (ticketing, CRM, ERP).
- **Advanced Context Engineering** to dynamically structure system instructions, conversation memory, retrieved knowledge chunks, and token budgets.
- **FastAPI** enterprise REST gateway featuring API authentication, Pydantic v2 validation, structured logging, and OpenAPI specifications.
- **Streamlit** client delivering an interactive support console, context inspection, citation verification, and administrative ingestion management.
- **Enterprise Testing & AI Evaluation** implementing Pytest test suites alongside automated RAG evaluation metrics (Faithfulness, Answer Relevance, Context Precision).

---

## 2. System Architecture

```
                                  USER / CLIENT LAYER
         ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
         │     Streamlit Web Console       │   │   External Enterprise Systems   │
         │  (Chat, Citations, Documents)   │   │     (Slack, Teams, Webhooks)    │
         └────────────────┬────────────────┘   └────────────────┬────────────────┘
                          │ HTTP / REST                         │ REST / JSON
                          ▼                                     ▼
═════════════════════════════════════════════════════════════════════════════════════════════
                              ENTERPRISE API GATEWAY (FastAPI)
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │ • TLS Termination & CORS Middleware        • API Key / JWT Bearer Authentication        │
 │ • Pydantic v2 Request Validation           • Request Correlation ID & Structured Logging│
 │ • Rate Limiting & Input Sanitization       • Global Exception Handlers (RFC 7807)       │
 └────────────────────────────────────────┬────────────────────────────────────────────────┘
                                          │
                                          ▼
═════════════════════════════════════════════════════════════════════════════════════════════
                      AGENT ORCHESTRATION LAYER (Google ADK & LangChain)
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │                                  SUPERVISOR AGENT                                       │
 │                 (Intent Routing, State Management, Plan Generation)                     │
 └─────────────┬──────────────────────────┬───────────────────────────────┬────────────────┘
               │                          │                               │
               ▼                          ▼                               ▼
 ┌───────────────────────────┐ ┌─────────────────────────────┐ ┌───────────────────────────┐
 │   KNOWLEDGE RETRIEVAL     │ │    SUPPORT ACTION AGENT     │ │   GUARDRAIL & EVALUATION  │
 │          AGENT            │ │       (MCP Tools)           │ │           AGENT           │
 │ (RAG, Citations, Qdrant)  │ │ (Tickets, CRM, Escalations) │ │ (PII, Policy, Grounding)  │
 └─────────────┬─────────────┘ └──────────────┬──────────────┘ └─────────────┬─────────────┘
               │                              │                              │
═══════════════╪══════════════════════════════╪══════════════════════════════╪══════════════
               │                              │                              │
               ▼                              ▼                              ▼
 ┌───────────────────────────┐ ┌─────────────────────────────┐ ┌───────────────────────────┐
 │  CONTEXT ENGINEERING      │ │   MODEL CONTEXT PROTOCOL    │ │    EVALUATION HARNESS     │
 │  • Dynamic Token Budgeter │ │        (MCP Subsystem)      │ │  • Faithfulness Metric    │
 │  • Sliding Memory Window  │ │  • FastMCP Ticketing Server │ │  • Answer Relevance       │
 │  • Citation Formatter     │ │  • FastMCP CRM Server       │ │  • Context Precision      │
 │  • System Prompt Builder  │ │  • ClientSession Transport  │ │  • Hallucination Monitor  │
 └─────────────┬─────────────┘ └──────────────┬──────────────┘ └───────────────────────────┘
               │                              │
               ▼                              ▼
═════════════════════════════════════════════════════════════════════════════════════════════
                               DATA & EXTERNAL SERVICE LAYER
 ┌───────────────────────────┐ ┌─────────────────────────────┐ ┌───────────────────────────┐
 │   Qdrant Vector Store     │ │  Enterprise Databases & APIs│ │   Google Gemini LLM /     │
 │  • Dense Embeddings       │ │  • IT Service Management    │ │   Embeddings API          │
 │  • Metadata Filtering     │ │  • Customer CRM Database    │ │  • gemini-2.5-flash       │
 │  • Chunk Level Payloads   │ │  • Enterprise Knowledge Repo│ │  • text-embedding-004     │
 └───────────────────────────┘ └─────────────────────────────┘ └───────────────────────────┘
```

---

## 3. Component Responsibilities

| Component | Responsibility | Tech Stack |
|---|---|---|
| **API Gateway** | Request authentication, input validation, rate limiting, request correlation IDs, routing, OpenAPI specs. | FastAPI, Pydantic v2, Uvicorn |
| **Supervisor Agent** | Analyzes incoming user messages, determines intent, coordinates sub-agents, aggregates multi-step answers. | Google ADK (`google.adk`), Gemini |
| **Knowledge Retrieval Agent** | Queries vector store, enforces similarity thresholds, extracts relevant document passages, appends verifiable metadata. | LangChain, `langchain-qdrant`, Qdrant Client |
| **Support Action Agent** | Executes actions (create support ticket, check order/incident status, escalate to human) using MCP tools. | Model Context Protocol (`mcp`), FastMCP |
| **Guardrail & Safety Agent** | Scans input/output for PII leaks, harmful content, prompt injections, and verifies claims against retrieved context. | Regex, Guardrail policies, LLM verification |
| **Context Engineering Engine** | Manages prompt assembly, enforces strict token budgeting, manages conversation history window, builds grounded instructions. | Python internal modules, `tiktoken` / Gemini tokenizer |
| **Vector Storage Engine** | Stores dense vector embeddings with rich payloads (source, page, department, access_level, timestamp). | Qdrant (`qdrant-client`, `langchain-qdrant`) |
| **MCP Tool Servers** | Hosts decoupled, sandboxed tools following the standard Model Context Protocol. | MCP Python SDK (`FastMCP`) |
| **Streamlit User Interface** | Provides enterprise chat UI, citation inspector, document upload portal, and agent telemetry view. | Streamlit, Requests/HTTPX |
| **AI Evaluation Framework** | Measures RAG quality, context precision, answer relevance, and faithfulness against ground truth. | Ragas / Custom LLM Judge, Pytest |

---

## 4. Data Flow

### 4.1 Document Ingestion Data Flow
```
[Enterprise Document (PDF/MD/TXT)]
       │
       ▼
[Document Loader & Sanitizer]
       │  (Extract raw text, strip harmful encoding, validate format)
       ▼
[Semantic / Recursive Chunker]
       │  (Chunk size: 800 tokens, Overlap: 150 tokens)
       ▼
[Metadata Extractor]
       │  (doc_id, filename, department, access_role, chunk_index, timestamp)
       ▼
[Google Gemini Embedding Generator]
       │  (Model: text-embedding-004, Dimension: 768)
       ▼
[Qdrant Collection Upsert]
       │  (Vector payload: chunk_text + metadata + access_control)
       ▼
[Indexed in Qdrant Vector DB]
```

### 4.2 Query Processing & Resolution Data Flow
```
1. User enters query in Streamlit / REST API.
2. Gateway authenticates API Key, sanitizes query, assigns `X-Correlation-ID`.
3. Supervisor Agent inspects intent:
   ├── Knowledge Query  ──> Knowledge Retrieval Agent
   ├── Action / Incident Request ──> Support Action Agent (MCP)
   └── Mixed Request    ──> Multi-step plan (Retrieve -> Execute Tool -> Synthesize)
4. Knowledge Agent computes embedding, performs Qdrant hybrid vector search with metadata filtering.
5. Context Engineering Engine allocates token budget, trims history, formats retrieved chunks with citation tags `[Source: DOC_ID, Page: N]`.
6. Supervisor executes LLM reasoning call via Gemini model with strict grounding prompt.
7. Support Action Agent triggers MCP tool (e.g. `create_support_ticket`) if required.
8. Guardrail Agent validates response against retrieved facts (Faithfulness check) and ensures no PII leakage.
9. Gateway returns JSON response with answer, citation objects, and execution trace.
10. Streamlit UI displays formatted answer with clickable source references and confidence score.
```

---

## 5. RAG Flow (Retrieval-Augmented Generation)

The RAG pipeline is engineered to prevent hallucinations and provide high-fidelity factual grounding:

```
                      Query: "How do I configure SAML SSO in Okta for our app?"
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │ Pre-Retrieval Filter  │ (Extract metadata filters:
                                    │ & Intent Rewriting    │  department="Security", role="IT_Admin")
                                    └───────────┬───────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │ Dense Vector Search   │ (Embedding: text-embedding-004)
                                    │ + Payload Filtering   │ (Qdrant HNSW cosine similarity)
                                    └───────────┬───────────┘
                                                │
                                    Top-K Chunks (e.g., K=10)
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │ Similarity Threshold  │ (Discard chunks with score < 0.72)
                                    │ & Reranking           │
                                    └───────────┬───────────┘
                                                │
                                    Top-N Filtered Chunks (N=4)
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │ Context Engineering   │ (Format: [Doc ID: #1 | Source: security.md])
                                    │ Dynamic Assembly      │ (Token budget check: <= 3000 tokens)
                                    └───────────┬───────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │ LLM Grounded Synthesis│ (Gemini 2.5/1.5: Answer strictly from context)
                                    └───────────┬───────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │ Post-Generation Audit │ (Verify every citation in answer matches
                                    │ & Citation Extraction │  retrieved doc ID)
                                    └───────────────────────┘
```

### Key RAG Safeguards:
1. **Source Attribution**: The LLM is instructed to cite explicit bracketed references `[Doc: <id>, Ch: <n>]`. Responses without grounding are rejected or flagged with lower confidence.
2. **Abstention Protocol**: If similarity scores fail to cross threshold $T = 0.72$, the agent explicitly responds: *"I do not have verified enterprise documentation to answer this question. Would you like me to open a support ticket for an IT specialist?"*
3. **Role-Based Chunk Filtering**: Queries carry user authorization tokens. Qdrant payload filters restrict retrieval to documents matching or lower than the user's role privilege level.

---

## 6. Agent Orchestration Flow (Google ADK & LangChain)

The agent system is architected as a hierarchical multi-agent supervisor pattern using the **Google Agent Development Kit (ADK)**:

```
                             ┌────────────────────────┐
                             │    User Request / Goal │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │    Supervisor Agent    │
                             │   (google.adk.Agent)   │
                             └───────────┬────────────┘
                                         │
                     ┌───────────────────┴───────────────────┐
                     │ Decide Delegation Path                │
                     ▼                                       ▼
        ┌─────────────────────────┐             ┌─────────────────────────┐
        │ Knowledge Agent (ADK)   │             │ Support Action Agent    │
        │ • Tool: qdrant_retriever│             │ • Tool: mcp_tool_runner │
        └────────────┬────────────┘             └────────────┬────────────┘
                     │ Returns: Context & Citations          │ Returns: Tool Execution Result
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Synthesis & Validation │
                             │ • Grounding Check      │
                             │ • Guardrail Scrubbing  │
                             └───────────┬────────────┘
                                         │
                                         ▼
                             ┌────────────────────────┐
                             │ Final Enterprise Answer│
                             └────────────────────────┘
```

### Delegation Rules:
- **Informational Inquiries**: Routed exclusively to the `Knowledge Agent`.
- **System Interactions (e.g. "Create ticket #402", "Reset token")**: Routed to the `Support Action Agent`, requiring affirmative confirmation before executing state-changing operations (Human-in-the-loop ready).
- **Hybrid Requests (e.g. "Find VPN policy and file a ticket if I can't connect")**: Sequential orchestration: Knowledge Agent retrieves VPN policy $\rightarrow$ checks preconditions $\rightarrow$ Support Action Agent executes ticket creation tool.

---

## 7. Model Context Protocol (MCP) Architecture

To avoid tightly coupling enterprise tool code to agent prompts, all tools are exposed via the **Model Context Protocol (MCP)** using the official MCP Python SDK (`mcp`).

```
 ┌────────────────────────────────────────────────────────┐
 │                      MCP CLIENT                        │
 │  • Embedded in Enterprise Agent runtime                │
 │  • Uses ClientSession from official `mcp` SDK           │
 │  • Supports `stdio_client` and `streamablehttp_client` │
 └───────────────────────────┬────────────────────────────┘
                             │ JSON-RPC 2.0 over Stdio/HTTP
           ┌─────────────────┴─────────────────┐
           ▼                                   ▼
 ┌───────────────────────────┐       ┌───────────────────────────┐
 │   FastMCP Ticketing Server│       │     FastMCP CRM Server    │
 │ (server/ticket_server.py) │       │   (server/crm_server.py)  │
 ├───────────────────────────┤       ├───────────────────────────┤
 │ Tools:                    │       │ Tools:                    │
 │ • create_ticket()         │       │ • get_customer_profile()  │
 │ • get_ticket_status()     │       │ • check_service_tier()    │
 │ • escalate_ticket()       │       │ • update_contact_info()   │
 │                           │       │                           │
 │ Prompts:                  │       │ Resources:                │
 │ • ticket_summary_prompt   │       │ • crm://accounts/{id}     │
 └───────────────────────────┘       └───────────────────────────┘
```

### Advantages of MCP in this Architecture:
1. **Process Isolation**: Tool logic runs in dedicated processes or containerized microservices, preventing tool failures from crashing the core agent.
2. **Strict Schema Contracts**: Tools are typed with Pydantic schemas and registered via `@mcp.tool()`, guaranteeing clean OpenAPI/JSON-RPC parameter definitions for Gemini.
3. **Security Boundaries**: Write tools enforce validation and credential checks independent of the LLM prompt.

---

## 8. Context Engineering Flow

Context engineering is a first-class subsystem responsible for maximizing LLM signal-to-noise ratio within a fixed token budget:

```
Total Context Window (e.g., Gemini 8k / 32k Budget Limit for Fast Latency)
┌──────────────────────────────────────────────────────────────────────────────────┐
│ [1] Core System Instructions & Enterprise Identity                    (~800 tok) │
├──────────────────────────────────────────────────────────────────────────────────┤
│ [2] Dynamic Tool Definitions & Schema Constraints (MCP / ADK)         (~600 tok) │
├──────────────────────────────────────────────────────────────────────────────────┤
│ [3] Grounding Context: Retrieved Chunks with Metadata Tags            (~2,500 tok)│
├──────────────────────────────────────────────────────────────────────────────────┤
│ [4] Sliding Window Conversation History (Pruned via Token Budget)     (~1,500 tok)│
├──────────────────────────────────────────────────────────────────────────────────┤
│ [5] Current User Message & Injected Runtime Variables                  (~400 tok)│
├──────────────────────────────────────────────────────────────────────────────────┤
│ [6] Reserved Output Buffer for LLM Generation                         (~2,000 tok)│
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Context Engineering Strategies:
1. **Dynamic Context Pruning**: History older than $N$ turns is compressed using semantic summarization if the conversation approaches the budget threshold.
2. **Metadata Chunk Framing**: Chunks are injected in structured XML/Markdown blocks:
   ```xml
   <context_chunk id="chunk_102" source="it_policies.pdf" page="14" department="IT">
   Employees must renew their VPN tokens every 90 days via the Okta security portal.
   </context_chunk>
   ```
3. **Explicit Negative Constraints**: "Answer ONLY from provided `<context_chunk>` tags. If the question cannot be answered from the provided chunks, reply with the standard fallback message."

---

## 9. API Architecture (FastAPI)

The REST API exposes clean, versioned endpoints (`/api/v1`) with full OpenAPI/Swagger documentation.

### 9.1 Endpoint Specifications

| Path | Method | Purpose | Auth Required |
|---|---|---|---|
| `/health` | `GET` | Service liveness, readiness, Qdrant connectivity | No |
| `/api/v1/query` | `POST` | Primary agent query (sync/async RAG resolution) | Yes (Bearer/API Key) |
| `/api/v1/chat` | `POST` | Stateful conversation query with session ID | Yes (Bearer/API Key) |
| `/api/v1/documents/ingest` | `POST` | Upload and index enterprise documents into Qdrant | Yes (Admin Scope) |
| `/api/v1/documents` | `GET` | List indexed documents and collection stats | Yes (Bearer/API Key) |
| `/api/v1/documents/{id}` | `DELETE` | Remove document chunks from vector index | Yes (Admin Scope) |
| `/api/v1/mcp/tools` | `GET` | Inspect registered MCP tool schemas and status | Yes (Bearer/API Key) |
| `/api/v1/eval/run` | `POST` | Trigger automated RAG evaluation test run | Yes (Admin Scope) |

### 9.2 Request/Response Contract (Pydantic v2)
```python
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="User question")
    session_id: Optional[str] = Field(default=None, description="Conversation session ID")
    department_filter: Optional[str] = Field(default=None, description="Filter documents by department")
    include_citations: bool = Field(default=True, description="Whether to include source citation metadata")

class Citation(BaseModel):
    document_id: str
    source_name: str
    page: Optional[int]
    chunk_index: int
    snippet: str
    relevance_score: float

class QueryResponse(BaseModel):
    query: str
    response: str
    citations: List[Citation]
    agent_used: str
    execution_time_ms: float
    confidence_score: float
```

---

## 10. Security Architecture

1. **Authentication & Authorization**:
   - Header-based API key authentication (`X-API-Key`) or JWT Bearer token authentication.
   - Role-Based Access Control (RBAC): `read:knowledge`, `write:tickets`, `admin:all`.
2. **Input Validation & Sanitization**:
   - Pydantic v2 validation on all request bodies.
   - Strict string sanitization to prevent prompt injection, control character escaping, and payload size restriction (max 10MB document uploads).
3. **Data Protection & PII Scrubbing**:
   - Automated regex scrubbing on user inputs and agent responses for Social Security Numbers (SSN), Credit Card Numbers, and corporate credentials before dispatching to external LLMs.
4. **Network & Secrets Management**:
   - Zero hardcoded secrets: All API keys loaded via `pydantic-settings` from environment variables.
   - Internal MCP servers communicate over isolated localhost `stdio` or internal Docker container networks.

---

## 11. Testing Architecture

The project enforces a three-tiered testing hierarchy:

```
                      ┌─────────────────────────────────┐
                      │    AI Evaluation (Ragas/Judge)   │  (Faithfulness, Relevance)
                      ├─────────────────────────────────┤
                      │    Integration Tests (Pytest)   │  (FastAPI + Qdrant + MCP)
                      ├─────────────────────────────────┤
                      │       Unit Tests (Pytest)       │  (Parsers, Budgeter, Config)
                      └─────────────────────────────────┘
```

1. **Unit Tests (`tests/unit/`)**:
   - Context Engineering token budget calculation and truncation.
   - Document chunking and metadata extraction.
   - Pydantic schema validation tests (boundary values, invalid types).
   - Config loading and fallback behavior.
2. **Integration Tests (`tests/integration/`)**:
   - Qdrant Vector Store integration using in-memory mode (`QdrantClient(":memory:")`).
   - MCP Server tool execution via `ClientSession`.
   - FastAPI endpoint testing using `httpx.AsyncClient` and mocked LLM calls.
3. **AI Evaluation Tests (`tests/eval/`)**:
   - Benchmark dataset of 20 representative enterprise questions with ground-truth answers and source contexts.
   - Scoring metrics:
     - **Faithfulness**: $\ge 0.85$ (No ungrounded claims).
     - **Answer Relevancy**: $\ge 0.85$ (Directly addresses the prompt).
     - **Context Recall**: $\ge 0.80$ (Retrieved chunks contain necessary facts).

---

## 12. Docker & Deployment Architecture

### 12.1 Multi-Container Topology (`docker-compose.yml`)
- **`qdrant`**: Official vector database image `qdrant/qdrant:v1.12.0` (ports: 6333, 6334) with persistent volume.
- **`api`**: Multi-stage Python 3.11-slim container running FastAPI with Uvicorn (port: 8000).
- **`ui`**: Streamlit web frontend container (port: 8501) communicating with `api` via internal Docker network.
- **`mcp-server`**: Standalone MCP tool service running ticket/CRM tools via Streamable HTTP or Stdio (port: 8080).

### 12.2 Production Container Best Practices
- Multi-stage Docker builds to reduce image footprint (<300MB).
- Non-root user execution (`appuser:10001`) for security compliance.
- Docker healthchecks configured for API (`/health`) and Qdrant (`/readyz`).
- Dedicated bridge network `enterprise-network` isolating internal services from external exposure.
