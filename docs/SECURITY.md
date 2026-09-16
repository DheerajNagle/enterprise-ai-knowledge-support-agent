# Application Security Architecture & Controls

## 1. Overview & Classification

This document outlines the **portfolio-level application security controls** designed and implemented for the **Enterprise AI Knowledge & Support Agent**. 

> [!IMPORTANT]
> **Honest Security Posture Disclaimer**:
> This project implements disciplined **portfolio-level application security controls** suitable for demonstration, internal evaluation, and reference architectures. It does **not** claim enterprise-grade certification, SOC 2 compliance, ISO/IEC 27001 certification, or FedRAMP authorization. Production deployments in regulated enterprise settings require additional infrastructure controls such as Hardware Security Modules (HSMs), enterprise Identity Providers (IdPs with OAuth 2.0 / OIDC), and external Web Application Firewalls (WAFs).

---

## 2. Implemented Security Controls

### A. Authentication & Secret Protection
- **Constant-Time Verification**: API Key verification uses `secrets.compare_digest` via `APIKeyAuthenticator` to prevent timing side-channel attacks during string comparison.
- **Dual Transport Support**: Validates credentials supplied via standard `X-API-Key` headers or `Authorization: Bearer <token>` authorization headers.
- **Credential Masking**: Secrets and credentials are never output in raw plaintext in user interfaces, audit traces, or console outputs (`mask_secret("sk-1234567890abcdef")` -> `sk-1...cdef`).

### B. Input Validation & Boundaries
- **Strict File Type Whitelisting**: Document ingestion strictly allows only:
  - `.pdf` (Portable Document Format)
  - `.txt` (Plain text)
  - `.md` (Markdown)
  All executable binaries (`.exe`), scripts (`.sh`, `.bat`, `.py`), macro-enabled documents (`.docm`), and unrecognized extensions are rejected with structured `UNSUPPORTED_FILE_TYPE` error envelopes.
- **File Size Limits**: Enforces a strict 10MB maximum ceiling per ingested document (`DEFAULT_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024`) preventing denial-of-service via memory exhaustion.
- **Request Body Size Limits**: Global middleware limits incoming JSON request payloads to 2MB (`DEFAULT_MAX_REQUEST_SIZE_BYTES = 2 * 1024 * 1024`), returning `413 Request Entity Too Large` upon violation.
- **Path Traversal Mitigation**: File path inputs are sanitized and checked using canonical resolution to prevent directory traversal escapes (`../../`).
- **Null Byte & Control Defanging**: Strips dangerous ASCII null bytes (`\x00`) and Unicode bidirectional override characters from incoming chat queries.

### C. Logging Sanitization
- **Automatic Log Redaction Filter**: A dedicated `RedactingLogFilter` (`logging.Filter`) intercepts all log records across the application.
- **Credential Redaction**: Regex patterns scan for and sanitize:
  - `API_KEY` / `apikey` values
  - `Bearer` tokens and JWT headers
  - `Authorization` headers
  - Passwords and client secrets
  - Private key blocks (`-----BEGIN PRIVATE KEY-----`)
  All matched sensitive values are converted to `[REDACTED]` prior to emission.

### D. Prompt Injection Defense & Untrusted Content Isolation
- **Adversarial Intent Detection**: `detect_prompt_injection()` analyzes incoming queries for known jailbreak signatures, system directive override attempts, and delimiter tampering, routing suspicious queries to `WorkflowType.SAFETY_REFUSAL`.
- **Retrieved-Document Instruction Isolation**: In RAG workflows, untrusted retrieved document content is defanged and encapsulated inside explicit XML boundaries (`<untrusted_document_content id="...">`) to instruct the LLM to treat document text strictly as inert reference data rather than executable directives.

---

## 3. Known Limitations & Threat Model Boundaries

| Threat / Risk | Portfolio-Level Control | Known Limitation | Recommended Production Enhancement |
| :--- | :--- | :--- | :--- |
| **Adversarial Prompt Injection** | Heuristic signature detection and passive XML isolation | Heuristic pattern matching cannot mathematically guarantee 100% defense against novel or semantic evasion | Deploy secondary LLM guardrail models (e.g. Llama Guard, NeMo Guardrails) and sandboxed execution |
| **Authentication** | Static API Key (`X-API-Key`) with constant-time verification | Lacks fine-grained RBAC, scope-based permissions, or automated rotation | Integrate OAuth 2.0 / OIDC IdP (Okta, Keycloak, Azure AD) with short-lived JWTs |
| **Malware in Uploads** | File extension whitelisting and PDF magic byte verification | Does not perform in-depth binary signature antivirus scanning | Route uploaded files through an isolated antivirus sandbox (e.g. ClamAV, AWS GuardDuty) |
| **Rate Limiting** | Connection limit / request size validation | In-memory limits do not provide distributed token-bucket throttling | Front the service with an API gateway (e.g. Kong, Envoy, Cloudflare) with IP/token rate limits |
| **Data At Rest** | Local SQLite and embedded Qdrant vector storage | Encryption at rest depends on underlying filesystem/OS encryption | Enable transparent database encryption (SQLCipher) and TLS for vector database clustering |

---

## 4. Security Verification

Automated security controls are verified in the test suite:
```bash
pytest tests/test_security.py -v
```
Covering:
1. Constant-time authentication and timing resistance
2. Rejection of unauthorized file types (`.exe`, `.py`, `.sh`, `.docx`)
3. File size and request payload size boundary enforcement
4. Log sanitization and credential masking
5. Prompt injection detection and document instruction isolation
6. Safe error responses preventing stack trace and credential leakage
