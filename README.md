# 🏢 Enterprise AI Knowledge Support Agent

An intelligent, enterprise-grade AI knowledge and support assistant powered by **Retrieval-Augmented Generation (RAG)**. This system enables organizations to connect internal wikis, manuals, policies, and ticketing databases into an interactive, high-accuracy conversational support engine.

---

## 🌟 Key Features

- **🔍 Intelligent Knowledge Retrieval (RAG)**: Combines semantic vector search with keyword/hybrid filtering to retrieve precise documents.
- **🛡️ Source Attribution & Citations**: Every response includes verifiable citations back to original internal documentation to minimize hallucinations.
- **🔐 Enterprise Security & RBAC**: Designed with role-based access control to ensure employees only query documents they are authorized to view.
- **⚡ High-Performance API**: Built on FastAPI with asynchronous request handling for enterprise scale.
- **🔌 Multi-LLM & Vector DB Agnostic**: Easily switch between OpenAI, Anthropic Claude, Google Gemini, or local models (Ollama), paired with ChromaDB, Pinecone, or Qdrant.

---

## 🏗️ System Architecture

```
   ┌───────────────────────┐
   │ Enterprise Data Sources │ (PDFs, Docs, Confluence, Jira, Notion)
   └───────────┬───────────┘
               │ (Chunking & Embeddings)
               ▼
   ┌───────────────────────┐
   │  Vector Database      │ (ChromaDB / Pinecone / Qdrant)
   └───────────┬───────────┘
               │ Hybrid Retrieval
               ▼
   ┌──────────────────────────────────────────────┐
   │ Enterprise AI Knowledge Support Agent (API) │
   │ ├── Context Reranking                        │
   │ ├── Citation Verification                    │
   │ └── LLM Reasoning                            │
   └───────────────────┬──────────────────────────┘
                       │
                       ▼
             [Verified Answer with Citations]
```

---

## 📁 Project Structure

```bash
enterprise-ai-knowledge-support-agent/
├── .env.example          # Sample environment configuration
├── .gitignore            # Git ignore specifications
├── README.md             # Project documentation
├── requirements.txt      # Python dependencies
└── src/
    ├── __init__.py
    ├── agent.py          # Core agent reasoning & query execution
    ├── config.py         # App & environment configuration
    └── main.py           # FastAPI application entrypoint
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/DheerajNagle/enterprise-ai-knowledge-support-agent.git
cd enterprise-ai-knowledge-support-agent
```

### 3. Setup Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment
Copy the example configuration and update your API keys:
```bash
cp .env.example .env
```

### 6. Run the Application
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
The API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check & service metadata |
| `POST` | `/api/v1/query` | Ask a question to the Knowledge Support Agent |
| `GET` | `/docs` | Interactive Swagger API documentation |

---

## 🛣️ Roadmap

- [x] Initial scaffolding & API foundation
- [ ] Connect multi-format document parser (PDF, DOCX, Markdown, HTML)
- [ ] Implement Hybrid Search (Dense Embeddings + BM25)
- [ ] Add conversation session management and streaming responses
- [ ] Webhook integration for Slack / Microsoft Teams / Web Chatbot

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
