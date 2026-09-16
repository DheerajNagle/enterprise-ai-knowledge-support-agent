# AI Evaluation Framework & Benchmark Suite

An automated, empirical evaluation harness for the Enterprise AI Knowledge & Support Agent. Benchmarks knowledge retrieval precision, source citation fidelity, multi-agent workflow classification, operational MCP tool execution, and adversarial prompt injection defenses.

---

## 1. Evaluation Architecture & Scope

The evaluation suite operates across three dedicated testing dimensions:

```
evaluation/
├── dataset.json            # 32 benchmark questions across 8 operational categories
├── evaluate_rag.py         # RAG retrieval hit rate, section precision, citations, and abstention
├── evaluate_agents.py      # End-to-end multi-tier agent routing, injection defense, timeouts
├── evaluate_tools.py       # MCP tool schemas, database execution correctness, validation
├── README.md               # Methodology, metrics definitions, and honest limitations
└── results/                # Timestamped empirical JSON benchmark runs
```

### Benchmark Dataset Categories (32 Synthetic Questions)

| Category | Count | Focus Area | Expected Workflow |
| :--- | :---: | :--- | :--- |
| `rag_factual` | 4 | Single-document policy facts (hours, PTO, refresh, per diem) | `RAG_ONLY` |
| `rag_multi_doc` | 4 | Multi-policy synthesis (remote work + expense, laptop + password) | `RAG_ONLY` |
| `mcp_tool` | 4 | Action requests (ticket lookup, employee profile, ticket creation) | `TOOL_ONLY` |
| `rag_mcp_hybrid` | 4 | Composite requests (check policy eligibility, then file ticket) | `HYBRID_RAG_TOOL` |
| `irrelevant` | 4 | Out-of-scope general domain queries (cooking, trivia, poetry) | `Direct LLM` / Refusal |
| `hallucination_test` | 4 | Fictitious company policies (dragon stipend, crypto bonuses) | `RAG_ONLY` (Refusal) |
| `prompt_injection` | 4 | Adversarial prompt leaks, DAN persona jailbreaks, tag injection | `SAFETY_REFUSAL` |
| `ambiguous` | 4 | Underspecified queries requiring clarification or broad triage | Contextual / Refusal |

---

## 2. Core Metrics Defined

All metrics are computed strictly from actual execution against the local vector database, SQLite database, and agent components. **Zero percentages are fabricated.**

1. **Retrieval Hit Rate (Recall@K)**:
   $$\text{Hit Rate} = \frac{\text{Queries with at least one expected document in top-k}}{\text{Total retrieval-eligible queries}}$$
2. **Source Citation Presence**:
   $$\text{Citation Compliance} = \frac{\text{Queries generating verified source citations}}{\text{Total retrieval-eligible queries}}$$
3. **Grounded Refusal Accuracy**:
   $$\text{Refusal Accuracy} = \frac{\text{Ungrounded / Hallucination queries properly refused}}{\text{Total refusal-eligible queries}}$$
4. **Workflow Classification Accuracy**:
   $$\text{Workflow Accuracy} = \frac{\text{Queries routed to correct workflow (RAG, Tool, Hybrid, Safety)}}{\text{Total workflow queries}}$$
5. **Prompt Injection Defense Rate**:
   $$\text{Injection Defense Rate} = \frac{\text{Adversarial queries intercepted and blocked}}{\text{Total prompt injection queries}}$$
6. **Tool Execution Success Rate**:
   $$\text{Tool Success Rate} = \frac{\text{Operational tool invocations completing successfully}}{\text{Total tool invocation tests}}$$
7. **Execution Latency**: Measured per-test round-trip time in milliseconds (ms).

---

## 3. How to Run Evaluations

Execute the evaluation runners using the project virtual environment:

### 1. Evaluate MCP Operational Tools
```bash
python evaluation/evaluate_tools.py
```

### 2. Evaluate RAG Retrieval & Citations
```bash
python evaluation/evaluate_rag.py
```

### 3. Evaluate Multi-Agent Orchestration
```bash
python evaluation/evaluate_agents.py
```

Reports are automatically timestamped and saved into `evaluation/results/`:
- `tools_eval_<timestamp>.json`
- `rag_eval_<timestamp>.json`
- `agent_eval_<timestamp>.json`

---

## 4. Limitations of the Evaluation Methodology

Honest disclosure of evaluation boundaries and synthetic constraints:

1. **Synthetic vs. Production Traffic**:
   The 32 benchmark questions are synthetically curated. Real enterprise users exhibit messy formatting, typos, multi-lingual queries, conversational drift, and domain-specific acronyms not fully captured in synthetic sets.
2. **Offline Fallback vs. Live LLM Generation**:
   When evaluating without a live Google Gemini API key, the system executes deterministic grounded synthesis. In this mode, semantic entailment is inferred through exact/lexical matches rather than model probability distributions.
3. **Keyword-Based Injection Detection**:
   Heuristic prompt injection filtering detects common adversarial patterns (e.g. `ignore instructions`, `DAN mode`, `system prompt leak`), but does not provide mathematical safety guarantees against novel, multi-token obfuscated jailbreaks.
4. **Binary Retrieval Hits**:
   Retrieval Hit Rate measures presence of the target document file, but does not measure token-level chunk overlap or semantic density within the chunk.
5. **Absence of Human-in-the-Loop Scoring**:
   Evaluation relies on automated regexes and expected metadata comparison. Subjective nuance, helpfulness, and tone are not captured by automated scoring harnesses.
