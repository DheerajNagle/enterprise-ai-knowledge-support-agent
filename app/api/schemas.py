"""
API Data Transfer Objects and Request/Response Schemas.

Defines Pydantic v2 schemas for request validation, response serialization,
structured error reporting, and system health status.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.database.models import TicketCategory, TicketPriority, TicketStatus


# ==============================================================================
# Health Check Schemas
# ==============================================================================

class ComponentHealth(BaseModel):
    """Health status of an individual subsystem."""
    status: str = Field(..., description="Operational status: healthy, degraded, or unavailable")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional diagnostic metadata")


class HealthResponse(BaseModel):
    """Foundation and operational health check contract."""
    status: str = Field(..., description="Overall service status (healthy, degraded)")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic application version")
    environment: str = Field(..., description="Deployment environment")
    gemini_configured: bool = Field(..., description="Whether Gemini LLM credentials are ready")
    qdrant_url: str = Field(..., description="Vector database endpoint URL")
    components: Optional[Dict[str, ComponentHealth]] = Field(
        default=None, description="Detailed component-level readiness status"
    )

    model_config = ConfigDict(extra="ignore")


# ==============================================================================
# Chat & Agent Schemas
# ==============================================================================

class ConversationTurnDTO(BaseModel):
    """Historical conversation turn passed for multi-turn context."""
    role: str = Field(..., description="Role of the speaker: 'user' or 'assistant'")
    content: str = Field(..., description="Text content of the message")


class RetrievedKnowledgeItemDTO(BaseModel):
    """Retrieved policy chunk and citation details."""
    filename: str = Field(..., description="Name of the source document file")
    section: str = Field(..., description="Document section or header")
    page_number: Optional[int] = Field(default=None, description="Page number if applicable")
    chunk_text: str = Field(..., description="Text content of the retrieved chunk")
    relevance_score: float = Field(..., description="Priority or similarity score")
    citation: str = Field(..., description="Formatted citation marker")


class ToolExecutionResultDTO(BaseModel):
    """Record of an MCP or database tool execution."""
    tool_name: str = Field(..., description="Name of the tool executed")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Input parameters passed to tool")
    result: Any = Field(..., description="Tool output or return payload")
    success: bool = Field(default=True, description="Whether execution completed without error")


class ChatRequest(BaseModel):
    """Input contract for conversational query dispatching."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="User inquiry or instruction to be processed by the agent",
        examples=["What is the remote work policy on core working hours?"],
    )
    user_id: Optional[str] = Field(default=None, description="Employee or user identifier")
    department: Optional[str] = Field(default=None, description="Department for query scoping")
    conversation_history: Optional[List[ConversationTurnDTO]] = Field(
        default=None, description="Previous conversational turns for context"
    )
    filter_criteria: Optional[Dict[str, Any]] = Field(
        default=None, description="Explicit retrieval filters (e.g., {'department': 'Engineering'})"
    )
    dry_run: bool = Field(default=False, description="Simulate action execution without database mutations")


class ChatResponse(BaseModel):
    """
    Unified 3-tier response contract returned by the API.
    Separates retrieved knowledge, operational tool results, and synthesized explanation.
    """
    request_id: str = Field(..., description="Unique request tracing ID")
    workflow: str = Field(..., description="Selected execution workflow: RAG_ONLY, TOOL_ONLY, HYBRID_RAG_TOOL, SAFETY_REFUSAL")
    response: str = Field(..., description="Conversational explanation delivered to the user")
    retrieved_knowledge: List[RetrievedKnowledgeItemDTO] = Field(
        default_factory=list, description="Tier 1: Retrieved knowledge chunks and citations"
    )
    tool_results: List[ToolExecutionResultDTO] = Field(
        default_factory=list, description="Tier 2: MCP tool executions and database action payloads"
    )
    llm_explanation: Optional[str] = Field(
        default=None, description="Tier 3: Grounded synthesis or action summary"
    )
    grounded: bool = Field(default=True, description="Whether response passed grounding verification")
    confidence_score: float = Field(default=1.0, description="Overall confidence score (0.0 - 1.0)")
    audit_logs: Optional[Dict[str, Any]] = Field(default=None, description="Routing and telemetry audit log")


# ==============================================================================
# Document Ingestion Schemas
# ==============================================================================

class IngestRequest(BaseModel):
    """Input contract for initiating knowledge base ingestion."""
    file_paths: Optional[List[str]] = Field(
        default=None, description="Specific file paths to load, chunk, embed, and index"
    )
    directory_path: Optional[str] = Field(
        default=None, description="Directory path containing corporate policies"
    )


class IngestResponse(BaseModel):
    """Summary report detailing document ingestion execution."""
    status: str = Field(..., description="Overall ingestion outcome (success, partial, failed)")
    files_processed: int = Field(..., description="Total document files processed")
    documents_loaded: int = Field(..., description="Total documents loaded from disk")
    chunks_created: int = Field(..., description="Total semantic chunks produced")
    vectors_upserted: int = Field(..., description="Total vector embeddings upserted to Qdrant")
    total_vectors_in_collection: int = Field(..., description="Current count of vectors in Qdrant collection")
    elapsed_seconds: float = Field(..., description="Total time taken in seconds")
    details: List[Dict[str, Any]] = Field(default_factory=list, description="File-by-file status details")


# ==============================================================================
# Support Ticket Schemas
# ==============================================================================

class TicketCreateRequest(BaseModel):
    """Input contract for submitting a new employee support ticket."""
    employee_id: str = Field(..., description="Valid employee ID submitting the ticket", examples=["EMP-001"])
    title: str = Field(..., min_length=3, max_length=255, description="Brief summary of the issue")
    description: str = Field(..., min_length=5, description="Detailed problem description")
    category: TicketCategory = Field(default=TicketCategory.GENERAL, description="Ticket category")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM, description="Initial priority level")


class TicketResponse(BaseModel):
    """Representation of an employee support ticket."""
    ticket_id: str = Field(..., description="Unique ticket identifier (TCK-YYYY-XXXXXX)")
    employee_id: str = Field(..., description="Associated employee ID")
    title: str = Field(..., description="Ticket title")
    description: str = Field(..., description="Ticket description")
    category: str = Field(..., description="Category code")
    priority: str = Field(..., description="Priority level")
    status: str = Field(..., description="Current status: OPEN, IN_PROGRESS, RESOLVED, CLOSED")
    resolution_notes: Optional[str] = Field(default=None, description="Resolution comments")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last modified timestamp")


class TicketListResponse(BaseModel):
    """List of support tickets matching query criteria."""
    tickets: List[TicketResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of returned tickets")


# ==============================================================================
# MCP Tool Schemas
# ==============================================================================

class ToolDefinitionDTO(BaseModel):
    """Schema descriptor for an available MCP tool."""
    name: str = Field(..., description="Identifier name of the tool")
    description: str = Field(..., description="Human-readable explanation of tool behavior")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema for parameters")


class ToolsListResponse(BaseModel):
    """List of registered tools available to agents and API clients."""
    tools: List[ToolDefinitionDTO] = Field(default_factory=list)
    count: int = Field(..., description="Number of available tools")


class ToolExecuteRequest(BaseModel):
    """Invocation payload for executing a named tool."""
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Input parameters passed to the tool")


class ToolExecuteResponse(BaseModel):
    """Result of direct tool execution."""
    tool_name: str = Field(..., description="Name of executed tool")
    success: bool = Field(..., description="Execution success flag")
    result: Any = Field(..., description="Return payload or error details")
    execution_time_seconds: float = Field(..., description="Elapsed execution duration in seconds")


# ==============================================================================
# Structured Error Schemas
# ==============================================================================

class ErrorDetail(BaseModel):
    """Structured error object conforming to enterprise API standards."""
    code: str = Field(..., description="Machine-readable error code (e.g. VALIDATION_ERROR, NOT_FOUND)")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: Optional[Any] = Field(default=None, description="Additional context or validation failure list")


class ErrorResponse(BaseModel):
    """Standardized top-level error response envelope."""
    error: ErrorDetail = Field(..., description="Error payload details")
    request_id: Optional[str] = Field(default=None, description="Request tracking ID")
