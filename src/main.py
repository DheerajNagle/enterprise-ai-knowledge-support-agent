from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.config import settings
from src.agent import KnowledgeAgent

app = FastAPI(
    title=settings.app_name,
    description="Enterprise AI Knowledge Support Agent API powered by RAG and LLM reasoning.",
    version="0.1.0",
)

agent = KnowledgeAgent()

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default_user"
    department: Optional[str] = "general"

class QueryResponse(BaseModel):
    query: str
    response: str
    citations: List[dict]
    confidence_score: float

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment
    }

@app.post("/api/v1/query", response_model=QueryResponse)
async def ask_agent(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    result = await agent.query(request.query)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host=settings.host, port=settings.port, reload=True)
