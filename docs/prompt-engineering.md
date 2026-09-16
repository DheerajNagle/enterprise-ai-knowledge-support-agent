# Enterprise Prompt Engineering Specification & Design Decisions

**Document ID:** DOC-ENG-2024-009  
**Version:** 1.2.0  
**Owner:** AI Architecture & Context Engineering Team  
**Applicability:** LLM Orchestrators, Agents, RAG Pipelines, and Evaluation Harvesters  

---

## 1. Executive Summary & Design Philosophy

The prompt engineering layer of the **Enterprise AI Knowledge & Support Agent** is designed as a software-engineered, versionable, and secure contract between the application runtime and the underlying Large Language Model (Gemini 2.5/1.5).

Rather than embedding ad-hoc natural language strings across business logic, all prompts are centralized in [`app/agent/prompts.py`](file:///e:/enterprise-ai-knowledge-support-agent/app/agent/prompts.py) with structured builder interfaces.

### Core Design Principles:
1. **Delimited Context Framing**: All dynamic variables (retrieved passages, conversation history, user questions) are encapsulated in explicit XML tags (`<retrieved_context>`, `<user_inquiry>`, `<context_chunk>`) to prevent confusion between system instructions and untrusted data.
2. **Strict Factual Grounding & Attribution**: The model is prohibited from incorporating unverified external assumptions into policy answers; every factual claim must carry an exact citation.
3. **Deterministic Abstention**: When retrieved evidence is incomplete, the system triggers a standardized refusal and escalation protocol rather than guessing.
4. **Security Boundaries & Injection Resistance**: Delimiters and explicit negative constraints protect against prompt injection, jailbreak attempts, and system prompt leakage.
5. **Semantic Versioning**: Prompts follow semantic versioning (`major.minor.patch`) tracked in `PROMPT_VERSIONS` for evaluation benchmarking and regression prevention.

---

## 2. Prompt Versioning & Registry Architecture

Prompts are version-tracked to allow continuous evaluation against benchmark datasets:

| Prompt Identifier | Current Version | Focus Area |
|---|---|---|
| `system_instruction` | `1.2.0` | Identity, governance, injection defense, security boundaries |
| `rag_answer_generation` | `1.2.0` | Context framing, citation syntax, negative constraints |
| `tool_usage` | `1.1.0` | Action gating, parameter validation, confirmation protocols |
| `grounding_verification` | `1.0.0` | Post-generation audit for ungrounded claims & hallucinations |
| `refusal_behavior` | `1.1.0` | Standardized abstention and support escalation templates |

---

## 3. Detailed Prompt Specifications

### 3.1 Core System Instruction (`SYSTEM_INSTRUCTION`)
- **Purpose**: Establishes the agent's persona as an authoritative Enterprise Knowledge & Support Assistant.
- **Key Enforcement Mechanisms**:
  - **Factual Grounding**: Instructs the model to treat the `<retrieved_context>` as its sole source of factual truth for enterprise inquiries.
  - **Distinguishing Facts from Guidance**: Directs the agent to explicitly state whether a response comes directly from official policy or is a general recommendation.
  - **Security Safeguards**: Explicitly forbids the disclosure of API keys, internal tokens, or database connection strings under any framing.
  - **Injection Resistance**: Hardens the model against prompt injection strings (e.g., "Ignore previous instructions", "Reveal system prompt", "Simulate DAN").

### 3.2 RAG Answer Generation Template (`RAG_ANSWER_TEMPLATE`)
- **Framing**:
  ```xml
  <system_directives>
  ... strict grounding & citation instructions ...
  </system_directives>

  <retrieved_context>
    <context_chunk index="1" id="DOC-leave-policy:p1:c1" source="leave_policy.md" section="2.1 Paid Time Off" page="1">
    ... chunk text ...
    </context_chunk>
  </retrieved_context>

  <conversation_history>
  User: ...
  Assistant: ...
  </conversation_history>

  <user_inquiry>
  ... question ...
  </user_inquiry>
  ```
- **Attribution Specification**: Requires citations in the format:
  ```text
  [Source: <filename>, Section: <section>, Page: <page>]
  ```
  Example: `[Source: leave_policy.md, Section: 2.1 Paid Time Off (PTO), Page: 1]`

### 3.3 Tool Usage Protocol (`TOOL_USAGE_INSTRUCTION`)
- **Purpose**: Enforces deterministic tool use and prevents hallucinated tool calls.
- **Rules**:
  - **Action Gating**: Tools are reserved exclusively for operations requiring live system state (querying tickets, creating tickets, looking up employees). Informational questions must not trigger tool calls.
  - **Parameter Completeness**: The agent must never invent required parameters (`employee_id`, `ticket_id`). If an employee requests an action without sufficient info, the agent must ask clarifying questions first.
  - **Post-Action Confirmation**: Mandates that tool outputs (e.g., generated Ticket ID `TCK-2024-XXXX`) are confirmed back to the user with clear next steps.

### 3.4 Grounding & Faithfulness Verification (`GROUNDING_VERIFICATION_PROMPT`)
- **Purpose**: Acts as an automated LLM-as-a-Judge inspection harness.
- **Audit Criteria**:
  1. *Faithfulness*: Does the context substantiate every claim?
  2. *Citation Integrity*: Are citations pointing to actual documents present in the retrieved set?
  3. *Zero Extrapolation*: Did the model invent numbers, dates, or contact emails?
- **Output Contract**: Structured JSON containing `is_grounded` boolean, `confidence_score`, and `audit_verdict` (`PASS`, `FAIL`, `NEEDS_REVISION`).

### 3.5 Refusal & Insufficient-Context Protocol (`INSUFFICIENT_CONTEXT_MESSAGE`)
- **Design Decision**: Acknowledging lack of documentation is vastly superior to generating speculative answers in an enterprise environment.
- **Response Elements**:
  1. Transparent statement that official documentation was searched but lacks the specific detail.
  2. Empathetic offer to open a support ticket on the user's behalf.
  3. Relevant contact email or department channel for immediate escalation.

---

## 4. Prompt Injection & Adversarial Defense

To defend against indirect prompt injection (e.g., untrusted document contents containing malicious instructions) and direct user jailbreaks:

1. **Tag Isolation**: User input and retrieved context are sandboxed inside isolated tags:
   - `<user_inquiry>`
   - `<retrieved_context>`
2. **Instruction Priority Hierarchy**: The model is instructed that instructions outside `<system_directives>` have zero authority to alter behavioral constraints.
3. **Heuristic Screening**: Pre-retrieval guardrails scan user inputs for common injection tokens before dispatching to LLM reasoning.

---

## 5. Token Budget Allocation

Context windows are strictly partitioned to guarantee low latency and prevent prompt truncation:

| Context Segment | Target Budget | Strategy |
|---|---|---|
| **System Instruction** | ~500 tokens | Fixed, immutable across requests |
| **Tool Definitions** | ~350 tokens | Formatted JSON-schema summaries |
| **Retrieved Context Chunks** | ~2,500 tokens | Top 3 to 5 chunks from Qdrant |
| **Conversation History** | ~1,200 tokens | Sliding window (last 3-5 turns) |
| **User Inquiry** | ~250 tokens | Sanitized user prompt |
| **Reserved Generation Buffer** | ~1,500 tokens | LLM response with citations |
| **Total Context Window** | **~6,300 tokens** | Well within Gemini's high-efficiency tier |

---

## 6. Testing & Validation Strategy

The prompt engineering subsystem is validated via automated unit tests in [`tests/test_prompts.py`](file:///e:/enterprise-ai-knowledge-support-agent/tests/test_prompts.py):
- Verification of XML tag closure and attribute preservation.
- Validation of injection resistance phrasing in system instructions.
- Verification of citation notation formatting.
- Verification of refusal messages and security denial responses.
- Version consistency checks against `PROMPT_VERSIONS`.
