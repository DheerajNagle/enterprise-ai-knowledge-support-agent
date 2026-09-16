"""
Tests for Gemini / LLM Response Generation Integration.

Validates:
- 100% offline mock client compatibility without live API keys
- Grounded answer generation with strict citations
- Three-tier response structure (Retrieved Knowledge, MCP Tool Results, LLM Explanation)
- Safe abstention and handling of missing / insufficient context
- Anti-hallucination citation validation
- Graceful degradation and error recovery
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from app.agent.schemas import (
    AssembledContext,
    ConversationTurn,
    PrioritizedChunk,
    QueryAnalysis,
    RetrievedKnowledgeItem,
    SourceMetadataItem,
    ToolExecutionResult,
)
from app.agent.prompts import INSUFFICIENT_CONTEXT_MESSAGE
from app.agent.llm_service import LLMService
from app.agent.root_agent import RootAgent, WorkflowType, AgentResponse
from app.agent.rag_agent import RAGAgent
from app.agent.tool_agent import MCPToolAgent
from app.mcp import EnterpriseMCPClient


# ------------------------------------------------------------------------------
# Mock Fixtures
# ------------------------------------------------------------------------------

@pytest.fixture
def mock_genai_client():
    """Provides a mocked google.genai.Client for asynchronous generation."""
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.models = MagicMock()

    # Default canned response
    mock_response = MagicMock()
    mock_response.text = (
        "Based on corporate policy, regular full-time employees who have completed "
        "their 90-day probationary period are eligible for remote work.\n\n"
        "Source:\nremote_work_policy.md\nSection:\nEligibility"
    )

    client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def sample_context():
    """Provides an AssembledContext fixture with realistic enterprise policy chunks."""
    chunk = PrioritizedChunk(
        chunk_id="chk_remote_001",
        doc_id="doc_remote",
        text="Full-time employees with satisfactory performance ratings may request up to 3 days remote work per week.",
        filename="remote_work_policy.md",
        section="Eligibility",
        page_number=1,
        vector_score=0.88,
        priority_score=0.92,
        estimated_tokens=45,
    )
    meta = SourceMetadataItem(
        doc_id="doc_remote",
        filename="remote_work_policy.md",
        section="Eligibility",
        page_number=1,
        chunk_id="chk_remote_001",
        relevance_score=0.92,
    )
    analysis = QueryAnalysis(
        original_query="What is the remote work eligibility?",
        sanitized_query="What is the remote work eligibility?",
        intent="KNOWLEDGE_INQUIRY",
        detected_department="HR",
        requires_tools=False,
    )
    return AssembledContext(
        user_query="What is the remote work eligibility?",
        query_analysis=analysis,
        conversation_history=[],
        retrieved_documents=[chunk],
        tool_results=[],
        system_instructions="Strict grounding.",
        constraints=["Cite every fact."],
        source_metadata=[meta],
        total_estimated_tokens=150,
        rendered_prompt="Document: remote_work_policy.md\nSection: Eligibility\nText...",
    )


# ------------------------------------------------------------------------------
# LLM Service Unit Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_grounded_rag_generation_with_citations(mock_genai_client, sample_context):
    """Verifies that LLMService calls Gemini async and extracts validated citations."""
    service = LLMService(model_name="gemini-2.0-flash", client=mock_genai_client)
    assert service.is_configured is True

    explanation = await service.generate_grounded_rag_answer(
        query="What is the remote work eligibility?",
        assembled_context=sample_context,
    )

    mock_genai_client.aio.models.generate_content.assert_called_once()
    assert explanation.grounded is True
    assert explanation.confidence_score > 0.8
    assert len(explanation.citations) > 0
    assert "remote_work_policy.md" in explanation.citations[0]
    assert "Eligibility" in explanation.citations[0]
    assert "Source:\nremote_work_policy.md\nSection:\nEligibility" in explanation.citations[0]


@pytest.mark.asyncio
async def test_insufficient_evidence_abstention(mock_genai_client):
    """Verifies that missing retrieved documents trigger immediate honest abstention without calling LLM."""
    service = LLMService(model_name="gemini-2.0-flash", client=mock_genai_client)

    empty_context = AssembledContext(
        user_query="What is the company policy on lunar travel?",
        query_analysis=QueryAnalysis(
            original_query="What is the company policy on lunar travel?",
            sanitized_query="What is the company policy on lunar travel?",
            intent="KNOWLEDGE_INQUIRY",
        ),
        conversation_history=[],
        retrieved_documents=[],  # Zero chunks
        tool_results=[],
        system_instructions="Test",
        source_metadata=[],
        total_estimated_tokens=50,
        rendered_prompt="No docs",
    )

    explanation = await service.generate_grounded_rag_answer(
        query="What is the company policy on lunar travel?",
        assembled_context=empty_context,
    )

    # Must NOT call the LLM model
    mock_genai_client.aio.models.generate_content.assert_not_called()
    assert explanation.grounded is False
    assert explanation.confidence_score == 0.0
    assert len(explanation.citations) == 0
    assert INSUFFICIENT_CONTEXT_MESSAGE in explanation.text


def test_citation_anti_hallucination_validation():
    """Verifies that citations mentioning unverified/unretrieved documents are discarded."""
    service = LLMService()
    allowed_docs = {"vpn_policy.md", "laptop_policy.md"}

    raw_citations = [
        "Source:\nvpn_policy.md\nSection:\nTroubleshooting",
        "Source:\nsecret_executive_bonus.pdf\nSection:\nPayouts",  # Hallucinated
        "Source:\nlaptop_policy.md\nSection:\nRefresh Cycle",
    ]

    valid = service.validate_citations(raw_citations, allowed_docs)
    assert len(valid) == 2
    assert any("vpn_policy.md" in c for c in valid)
    assert any("laptop_policy.md" in c for c in valid)
    assert not any("secret_executive_bonus.pdf" in c for c in valid)


@pytest.mark.asyncio
async def test_no_api_key_graceful_fallback(sample_context):
    """Verifies that LLMService gracefully falls back to deterministic grounded synthesis when no API key exists."""
    service = LLMService(api_key="", client=None)
    assert service.is_configured is False

    explanation = await service.generate_grounded_rag_answer(
        query="What is remote work eligibility?",
        assembled_context=sample_context,
    )

    assert explanation.grounded is True
    assert explanation.model_name == "grounded-deterministic-fallback"
    assert "remote_work_policy.md" in explanation.text
    assert len(explanation.citations) > 0


@pytest.mark.asyncio
async def test_llm_api_error_handling(mock_genai_client, sample_context):
    """Verifies that API errors (e.g. 429 quota or network timeout) degrade gracefully without crashing."""
    mock_genai_client.aio.models.generate_content.side_effect = RuntimeError("ResourceExhausted: 429 Quota Exceeded")

    service = LLMService(client=mock_genai_client)
    explanation = await service.generate_grounded_rag_answer(
        query="What is remote work eligibility?",
        assembled_context=sample_context,
    )

    # Should safely fallback to deterministic grounded answer
    assert explanation.grounded is True
    assert explanation.model_name == "grounded-deterministic-fallback"
    assert "remote_work_policy.md" in explanation.text


# ------------------------------------------------------------------------------
# Three-Tier Response Architecture Tests
# ------------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_root_agent(mock_genai_client):
    """Creates a RootAgent with mock LLM and live MCP client with clean teardown."""
    mcp = EnterpriseMCPClient()
    await mcp.connect()

    try:
        llm = LLMService(client=mock_genai_client)
        agent = RootAgent(
            mcp_client=mcp,
            llm_service=llm,
        )
        yield agent
    finally:
        await mcp.disconnect()


@pytest.mark.asyncio
async def test_three_tier_response_rag_only(test_root_agent):
    """
    Verifies that RAG_ONLY workflow returns:
    1. Populated retrieved_knowledge with source citations
    2. Empty tool_results
    3. Populated llm_explanation
    """
    query = "What is the remote work equipment allowance?"
    response = await test_root_agent.run(query=query)

    assert isinstance(response, AgentResponse)
    assert response.workflow == WorkflowType.RAG_ONLY

    # 1. Retrieved Knowledge
    assert len(response.retrieved_knowledge) > 0
    item = response.retrieved_knowledge[0]
    assert isinstance(item, RetrievedKnowledgeItem)
    assert item.filename == "remote_work_policy.md"
    assert "Source:" in item.citation
    assert "Section:" in item.citation

    # 2. Tool Results (Must be empty for RAG_ONLY)
    assert len(response.tool_results) == 0

    # 3. LLM Explanation
    assert response.llm_explanation is not None
    assert len(response.llm_explanation) > 0


@pytest.mark.asyncio
async def test_three_tier_response_tool_only(test_root_agent):
    """
    Verifies that TOOL_ONLY workflow returns:
    1. Empty retrieved_knowledge
    2. Populated tool_results with operational parameters and payload
    3. Populated llm_explanation
    """
    query = "Create a ticket because my laptop display is flickering"
    response = await test_root_agent.run(query=query)

    assert isinstance(response, AgentResponse)
    assert response.workflow == WorkflowType.TOOL_ONLY

    # 1. Retrieved Knowledge (Must be empty for TOOL_ONLY)
    assert len(response.retrieved_knowledge) == 0

    # 2. Tool Results
    assert len(response.tool_results) == 1
    tool_exec = response.tool_results[0]
    assert isinstance(tool_exec, ToolExecutionResult)
    assert tool_exec.tool_name == "create_support_ticket"
    assert tool_exec.success is True
    assert "ticket_id" in tool_exec.result.get("ticket", {})

    # 3. LLM Explanation
    assert response.llm_explanation is not None
    assert "TCK-" in response.response_text


@pytest.mark.asyncio
async def test_three_tier_response_hybrid(test_root_agent):
    """
    Verifies that HYBRID_RAG_TOOL workflow distinctly populates ALL 3 TIERS:
    1. retrieved_knowledge (policy citations)
    2. tool_results (ticket creation)
    3. llm_explanation (synthesized policy + action reasoning)
    """
    query = "What does the VPN policy say and create a ticket if my issue qualifies?"
    response = await test_root_agent.run(query=query)

    assert isinstance(response, AgentResponse)
    assert response.workflow == WorkflowType.HYBRID_RAG_TOOL

    # 1. Retrieved Knowledge
    assert len(response.retrieved_knowledge) > 0
    assert any("vpn_policy.md" in k.filename for k in response.retrieved_knowledge)

    # 2. Tool Results
    assert len(response.tool_results) == 1
    assert response.tool_results[0].tool_name == "create_support_ticket"
    assert response.tool_results[0].success is True

    # 3. LLM Explanation
    assert response.llm_explanation is not None
    assert "### Policy Evaluation" in response.response_text
    assert "### Action Taken" in response.response_text
