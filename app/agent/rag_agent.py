"""
Google ADK RAG Specialized Agent.

Implements the enterprise knowledge retrieval agent using Google Agent Development Kit (ADK).
Specialized in searching and synthesizing company policy answers with strict grounding,
citation preservation, and indirect prompt injection defenses.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from google.adk import Agent
from app.config import get_settings
from app.rag.retriever import RetrievalResult
from app.agent.prompts import (
    INSUFFICIENT_CONTEXT_MESSAGE,
    SECURITY_REFUSAL_MESSAGE,
    SYSTEM_INSTRUCTION,
)
from app.agent.context import ContextEngine
from app.agent.schemas import (
    AssembledContext,
    ConversationTurn,
    LLMExplanation,
    RetrievedKnowledgeItem,
    SourceMetadataItem,
)
from app.agent.llm_service import LLMService
from app.mcp import EnterpriseMCPClient

logger = logging.getLogger("enterprise_agent.rag_agent")

RAG_AGENT_INSTRUCTION = f"""{SYSTEM_INSTRUCTION}

You are the Specialized RAG Knowledge Agent in the Enterprise AI hierarchy.
Your sole mission is to answer enterprise policy, HR, IT, security, and benefits inquiries.
Adhere strictly to these principles:
1. Answer ONLY using the facts present in the retrieved context chunks.
2. For every factual assertion, cite the exact source:
   Source:
   <filename>
   Section:
   <section>
3. If the retrieved context is empty, ambiguous, or lacks the necessary facts, state:
   "{INSUFFICIENT_CONTEXT_MESSAGE}"
4. Do NOT speculate, infer, or hallucinate beyond what is stated in the policy text.
"""


class RAGAgentResult(BaseModel):
    """Structured response emitted by RAGAgent."""

    answer: str = Field(..., description="Grounded answer to the knowledge query")
    sources: List[SourceMetadataItem] = Field(
        default_factory=list, description="List of cited source documents and chunks"
    )
    assembled_context: AssembledContext = Field(..., description="Curated context pipeline artifact")
    is_grounded: bool = Field(default=True, description="True if answer is directly backed by context")
    confidence_score: float = Field(default=1.0, description="Confidence score between 0.0 and 1.0")
    retrieved_knowledge: List[RetrievedKnowledgeItem] = Field(
        default_factory=list, description="Structured knowledge chunks retrieved with provenance"
    )
    llm_explanation: Optional[LLMExplanation] = Field(
        default=None, description="Detailed LLM explanation metadata"
    )


class RAGAgent:
    """
    Specialized Knowledge Retrieval Agent built on Google ADK.
    Integrates Context Engineering and LLMService to guarantee groundedness,
    anti-hallucination citations, and safe abstention.
    """

    def __init__(
        self,
        mcp_client: Optional[EnterpriseMCPClient] = None,
        context_engine: Optional[ContextEngine] = None,
        llm_service: Optional[LLMService] = None,
        model_name: Optional[str] = None,
    ):
        settings = get_settings()
        self.mcp_client = mcp_client
        self.context_engine = context_engine or ContextEngine()
        self.model_name = model_name or settings.gemini_model
        self.llm_service = llm_service or LLMService(model_name=self.model_name)

        # Underlying official Google ADK Agent definition
        self.adk_agent = Agent(
            name="rag_agent",
            model=self.model_name,
            description="Specialized agent for retrieving and synthesizing enterprise policy information.",
            instruction=RAG_AGENT_INSTRUCTION,
        )

    async def run(
        self,
        query: str,
        conversation_history: Optional[List[ConversationTurn]] = None,
        top_k: int = 3,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> RAGAgentResult:
        """
        Executes knowledge retrieval, context engineering, and grounded answer synthesis.
        """
        logger.info("[RAGAgent] Processing knowledge query: '%s'", query)

        # 1. First run query analysis from Context Engine
        analysis = self.context_engine.analyze_query(query)

        # 2. Safety / Prompt Injection Check
        if analysis.is_potential_injection:
            logger.warning("[RAGAgent] Prompt injection heuristics triggered on query: %s", query)
            assembled = self.context_engine.assemble(
                query=query,
                retrieved_chunks=[],
                conversation_history=conversation_history,
            )
            return RAGAgentResult(
                answer=SECURITY_REFUSAL_MESSAGE,
                sources=[],
                assembled_context=assembled,
                is_grounded=True,
                confidence_score=1.0,
                retrieved_knowledge=[],
                llm_explanation=LLMExplanation(
                    text=SECURITY_REFUSAL_MESSAGE,
                    model_name=self.model_name,
                    grounded=True,
                    confidence_score=1.0,
                    citations=[],
                ),
            )

        # 3. Retrieve through MCP Client (search_policy) if available
        retrieved_candidates = None
        if self.mcp_client is not None:
            dept = filter_criteria.get("department") if filter_criteria else analysis.detected_department
            try:
                if not self.mcp_client.is_connected:
                    await self.mcp_client.connect()
                policy_res = await self.mcp_client.search_policy(query=query, department=dept, top_k=top_k * 2)
                results_data = policy_res.get("results", [])
                retrieved_candidates = [
                    RetrievalResult(
                        chunk_id=r["chunk_id"],
                        doc_id=r.get("doc_id", "doc"),
                        text=r["text"],
                        filename=r["filename"],
                        section=r.get("section", "General"),
                        page_number=r.get("page_number"),
                        score=r.get("relevance_score", 0.7),
                    )
                    for r in results_data
                ]
            except Exception as exc:
                logger.warning("[RAGAgent] MCP search_policy failed: %s. Using local retriever.", exc)

        # 4. Context Engineering Pipeline (Filtering, Prioritization, Token Budgeting, Assembly)
        assembled = self.context_engine.assemble(
            query=query,
            retrieved_chunks=retrieved_candidates,
            conversation_history=conversation_history,
            top_k=top_k,
            filter_criteria=filter_criteria,
        )

        # 5. Build structured RetrievedKnowledgeItem entries
        retrieved_knowledge = [
            RetrievedKnowledgeItem(
                filename=doc.filename,
                section=doc.section,
                page_number=doc.page_number,
                chunk_text=doc.text,
                relevance_score=round(doc.priority_score, 4),
                citation=f"Source:\n{doc.filename}\nSection:\n{doc.section}",
            )
            for doc in assembled.retrieved_documents
        ]

        # 6. Insufficient Context Check
        if not assembled.retrieved_documents:
            logger.info("[RAGAgent] No relevant chunks passed filtering for query: '%s'", query)
            return RAGAgentResult(
                answer=INSUFFICIENT_CONTEXT_MESSAGE,
                sources=[],
                assembled_context=assembled,
                is_grounded=False,
                confidence_score=0.0,
                retrieved_knowledge=[],
                llm_explanation=LLMExplanation(
                    text=INSUFFICIENT_CONTEXT_MESSAGE,
                    model_name=self.model_name,
                    grounded=False,
                    confidence_score=0.0,
                    citations=[],
                ),
            )

        # 7. Grounded Generation via LLMService
        llm_explanation = await self.llm_service.generate_grounded_rag_answer(
            query=query,
            assembled_context=assembled,
        )

        return RAGAgentResult(
            answer=llm_explanation.text,
            sources=assembled.source_metadata,
            assembled_context=assembled,
            is_grounded=llm_explanation.grounded,
            confidence_score=llm_explanation.confidence_score,
            retrieved_knowledge=retrieved_knowledge,
            llm_explanation=llm_explanation,
        )
