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
from app.agent.schemas import AssembledContext, ConversationTurn, SourceMetadataItem
from app.mcp import EnterpriseMCPClient

logger = logging.getLogger("enterprise_agent.rag_agent")

RAG_AGENT_INSTRUCTION = f"""{SYSTEM_INSTRUCTION}

You are the Specialized RAG Knowledge Agent in the Enterprise AI hierarchy.
Your sole mission is to answer enterprise policy, HR, IT, security, and benefits inquiries.
Adhere strictly to these principles:
1. Answer ONLY using the facts present in the retrieved context chunks.
2. For every factual assertion, append the exact source citation: [Source: <filename>, Section: <section>, Page: <page>].
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


class RAGAgent:
    """
    Specialized Knowledge Retrieval Agent built on Google ADK.
    Integrates the Context Engineering pipeline to avoid document stuffing
    and provide verifiable citations.
    """

    def __init__(
        self,
        mcp_client: Optional[EnterpriseMCPClient] = None,
        context_engine: Optional[ContextEngine] = None,
        model_name: Optional[str] = None,
    ):
        settings = get_settings()
        self.mcp_client = mcp_client
        self.context_engine = context_engine or ContextEngine()
        self.model_name = model_name or settings.gemini_model

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

        # 5. Insufficient Context Check
        if not assembled.retrieved_documents:
            logger.info("[RAGAgent] No relevant chunks passed filtering for query: '%s'", query)
            return RAGAgentResult(
                answer=INSUFFICIENT_CONTEXT_MESSAGE,
                sources=[],
                assembled_context=assembled,
                is_grounded=False,
                confidence_score=0.0,
            )

        # 4. Synthesize Grounded Response
        # Try live Gemini LLM if configured, otherwise synthesize grounded extraction
        settings = get_settings()
        answer = ""
        if settings.is_gemini_configured:
            try:
                from google import genai
                client = genai.Client(api_key=settings.gemini_api_key)
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=assembled.rendered_prompt,
                )
                answer = response.text.strip() if response.text else ""
            except Exception as exc:
                logger.warning("[RAGAgent] Live Gemini API invocation failed: %s. Falling back to local synthesis.", exc)

        if not answer:
            # Deterministic, grounded extraction from prioritized chunks
            top_chunk = assembled.retrieved_documents[0]
            answer_parts = [
                f"Based on the {top_chunk.filename} (Section: {top_chunk.section}):\n",
                f"{top_chunk.text}\n",
            ]
            # Include secondary chunk if available
            if len(assembled.retrieved_documents) > 1:
                sec_chunk = assembled.retrieved_documents[1]
                answer_parts.append(
                    f"\nAdditional Details ({sec_chunk.filename}, Section: {sec_chunk.section}):\n{sec_chunk.text}"
                )

            # Append formal citations
            answer_parts.append("\n\nCitations:")
            for meta in assembled.source_metadata:
                pg = f", Page {meta.page_number}" if meta.page_number else ""
                answer_parts.append(f"- [Source: {meta.filename}, Section: {meta.section}{pg}]")

            answer = "\n".join(answer_parts)

        return RAGAgentResult(
            answer=answer,
            sources=assembled.source_metadata,
            assembled_context=assembled,
            is_grounded=True,
            confidence_score=round(assembled.retrieved_documents[0].priority_score, 4),
        )
