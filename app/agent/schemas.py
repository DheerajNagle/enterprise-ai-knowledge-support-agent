"""
Pydantic Schemas for Context Engineering Pipeline.

Defines structured data models representing query analysis, conversation context,
prioritized chunks, tool outputs, and the final assembled context contract.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


def utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class QueryAnalysis(BaseModel):
    """Result of analyzing an incoming user query."""

    original_query: str = Field(..., description="Raw incoming query text")
    sanitized_query: str = Field(..., description="Sanitized query text with control chars removed")
    intent: str = Field(
        default="KNOWLEDGE_INQUIRY",
        description="Classified intent: KNOWLEDGE_INQUIRY, ACTION_REQUEST, HYBRID, or GENERAL",
    )
    detected_department: Optional[str] = Field(
        default=None, description="Department inferred from keywords (HR, IT, Finance, Security, Legal)"
    )
    requires_tools: bool = Field(
        default=False, description="Whether query requires live tool interaction"
    )
    keywords: List[str] = Field(
        default_factory=list, description="Salient keywords extracted from query"
    )
    is_potential_injection: bool = Field(
        default=False, description="True if query exhibits prompt injection heuristics"
    )
    safety_flags: List[str] = Field(
        default_factory=list, description="Specific safety heuristic flags triggered"
    )


class ConversationTurn(BaseModel):
    """Represents a single turn in a multi-turn conversation history."""

    role: str = Field(..., description="Speaker role: user, assistant, system, or tool")
    content: str = Field(..., description="Message text content")
    timestamp: str = Field(default_factory=utc_now_iso, description="Message timestamp")


class ToolResultItem(BaseModel):
    """Represents an execution result from an internal tool (e.g. MCP / Database)."""

    tool_name: str = Field(..., description="Name of the invoked tool")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters passed to the tool"
    )
    result: Any = Field(..., description="Output payload or return value")
    status: str = Field(default="success", description="Execution status: success or error")
    execution_time_ms: float = Field(default=0.0, description="Execution duration in milliseconds")


class SourceMetadataItem(BaseModel):
    """Citation-ready metadata tracking the provenance of retrieved information."""

    doc_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Source filename")
    section: str = Field(default="General", description="Section or heading title")
    page_number: Optional[int] = Field(default=None, description="Page number if applicable")
    chunk_id: str = Field(..., description="Unique chunk identifier")
    relevance_score: float = Field(..., description="Final relevance or priority score")


class PrioritizedChunk(BaseModel):
    """A document chunk enriched with prioritization, sanitization, and token metrics."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Document identifier")
    text: str = Field(..., description="Sanitized chunk text content")
    filename: str = Field(..., description="Source document filename")
    section: str = Field(default="General", description="Section heading")
    page_number: Optional[int] = Field(default=None, description="Page number")
    vector_score: float = Field(..., description="Original vector similarity score")
    priority_score: float = Field(..., description="Engineered priority score considering recency, coverage, and rank")
    estimated_tokens: int = Field(..., description="Estimated token count for budgeting")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Underlying chunk metadata")


class AssembledContext(BaseModel):
    """
    Final structured context object passed to LLM reasoning.
    Avoids uncurated document stuffing and guarantees token budgeting.
    """

    user_query: str = Field(..., description="Target user question")
    query_analysis: QueryAnalysis = Field(..., description="Analysis metrics for the query")
    conversation_history: List[ConversationTurn] = Field(
        default_factory=list, description="Curated conversation turns within budget"
    )
    retrieved_documents: List[PrioritizedChunk] = Field(
        default_factory=list, description="Curated, deduplicated, sanitized, and prioritized chunks"
    )
    tool_results: List[ToolResultItem] = Field(
        default_factory=list, description="Results from any preceding tool calls"
    )
    system_instructions: str = Field(..., description="System governance prompt")
    constraints: List[str] = Field(
        default_factory=list, description="Active operational and security constraints"
    )
    source_metadata: List[SourceMetadataItem] = Field(
        default_factory=list, description="Citation provenance for all included chunks"
    )
    total_estimated_tokens: int = Field(..., description="Estimated total token footprint of the assembled prompt")
    filtered_chunks_count: int = Field(default=0, description="Number of candidate chunks dropped during filtering")
    dropped_due_to_budget_count: int = Field(default=0, description="Number of chunks dropped due to token budget limit")
    rendered_prompt: str = Field(..., description="Complete, formatted prompt string ready for LLM generation")


class RetrievedKnowledgeItem(BaseModel):
    """Structured representation of a retrieved document passage with provenance."""

    filename: str = Field(..., description="Source policy filename")
    section: str = Field(default="General", description="Section or policy heading")
    page_number: Optional[int] = Field(default=None, description="Page number if applicable")
    chunk_text: str = Field(..., description="Content text of the retrieved passage")
    relevance_score: float = Field(..., description="Similarity or priority score")
    citation: str = Field(..., description="Formatted citation label (Source: ... Section: ...)")


class ToolExecutionResult(BaseModel):
    """Structured representation of an executed tool action."""

    tool_name: str = Field(..., description="Name of the invoked tool")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters passed to tool")
    result: Any = Field(..., description="Structured payload or output returned by tool")
    success: bool = Field(default=True, description="Whether execution succeeded")
    execution_time_ms: float = Field(default=0.0, description="Execution duration in milliseconds")


class LLMExplanation(BaseModel):
    """Structured representation of an LLM-generated grounded explanation."""

    text: str = Field(..., description="Synthesized natural language explanation")
    model_name: str = Field(..., description="Model identifier used for generation")
    grounded: bool = Field(default=True, description="Whether answer is strictly grounded in retrieved evidence")
    confidence_score: float = Field(default=1.0, description="Confidence metric for the answer")
    citations: List[str] = Field(default_factory=list, description="Verified citations extracted from answer")
