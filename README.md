# 🏢 Enterprise AI Knowledge & Support Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, multi-agent AI knowledge and support platform powered by **Google Agent Development Kit (ADK)**, **Gemini 2.5/1.5**, **Retrieval-Augmented Generation (RAG)**, **Qdrant Vector Database**, and the **Model Context Protocol (MCP)**.

---

## 📑 Documentation

- **System Architecture**: Detailed in [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Master Implementation Plan**: Detailed in [`PROJECT_PLAN.md`](PROJECT_PLAN.md)

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Language & Runtime** | Python 3.11+ |
| **API & Gateway** | FastAPI, Uvicorn, Pydantic v2, Pydantic-Settings, HTTPX |
| **Agent Orchestration** | Google Agent Development Kit (ADK), LangChain |
| **LLM & Reasoning** | Google Gemini (Gemini 2.5 / 1.5 Series) |
| **Vector Database & RAG** | Qdrant (`qdrant-client`, `langchain-qdrant`), Text-Embedding-004 |
| **Tool Execution** | Model Context Protocol (MCP Python SDK, FastMCP, ClientSession) |
| **User Interface** | Streamlit |
| **Containerization** | Docker, Docker Compose (Multi-stage build) |
| **Quality & Evaluation** | Pytest, Pytest-Asyncio, Ragas |

---

## 📁 Application Structure

```
enterprise-ai-knowledge-support-agent/
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── ARCHITECTURE.md           # System architecture specification
├── PROJECT_PLAN.md           # 10-Phase implementation plan
├── Dockerfile                # Production multi-stage Docker build
├── docker-compose.yml        # Multi-container orchestration (API + Qdrant)
├── pyproject.toml            # Project metadata & dependency definitions
├── README.md                 # Project documentation
├── app/                      # Application source package
│   ├── __init__.py           # Package marker
│   ├── config.py             # Strongly typed Settings & configuration validation
│   └── main.py               # FastAPI entrypoint with GET /health
├── data/                     # Data directory for enterprise documents & indices
│   └── .gitkeep
├── docs/                     # Documentation & specifications
│   └── .gitkeep
└── tests/                    # Test suite
    ├── __init__.py           # Test package marker
    ├── test_config.py        # Configuration & validation tests
    └── test_health.py        # Foundation health endpoint tests
```

---

## ⚙️ Environment Configuration

Copy the sample environment file and configure your credentials:

```bash
cp .env.example .env
```

Key environment variables:
- `GEMINI_API_KEY`: Google Gemini API key for LLM operations.
- `QDRANT_URL`: Endpoint for Qdrant vector database (default: `http://localhost:6333`).
- `QDRANT_API_KEY`: Optional key for Qdrant Cloud.
- `API_KEY`: Secret authentication key for API Gateway requests.
- `ENVIRONMENT`: `development`, `staging`, `production`, or `test`.

---

## 🚀 How to Run the Project

### 1. Local Python Environment (Recommended for Development)

#### Prerequisites
- Python 3.11+ installed

#### Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

#### Install Dependencies
```bash
pip install -e .
# Or using pip with pyproject.toml:
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv pytest httpx
```

#### Run the FastAPI Gateway
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The service will start at [http://localhost:8000](http://localhost:8000).
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- Interactive API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 2. Docker & Docker Compose

To start both the API gateway and Qdrant vector database:

```bash
docker compose up -d --build
```

Check service status:
```bash
docker compose ps
```

Stop services:
```bash
docker compose down
```

---

## 🧪 Running Tests

Execute the Pytest test suite:

```bash
# Run all tests with verbose output
pytest -v

# Run specific test modules
pytest tests/test_config.py
pytest tests/test_health.py
```

---

## 🗺️ Implementation Roadmap

- [x] **Phase 1: Project Foundation & Architecture** (Structure, Configuration, Healthcheck, Docker, Pytest)
- [ ] **Phase 2: Configuration, Structured Logging & Pydantic v2 Core Schemas**
- [ ] **Phase 3: Knowledge Ingestion & Vector Storage Pipeline (Qdrant & Embeddings)**
- [ ] **Phase 4: Context Engineering, Prompt Engineering & Advanced RAG Engine**
- [ ] **Phase 5: Model Context Protocol (MCP) Server & Client Subsystem**
- [ ] **Phase 6: Google ADK & Multi-Agent Orchestration Engine**
- [ ] **Phase 7: Enterprise FastAPI REST Gateway & Security Layer**
- [ ] **Phase 8: Streamlit Production Support Console & Citations UI**
- [ ] **Phase 9: AI Evaluation & Automated Quality Harness (Ragas / LLM-as-a-Judge)**
- [ ] **Phase 10: Dockerization, Container Networking & Production Verification**

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
