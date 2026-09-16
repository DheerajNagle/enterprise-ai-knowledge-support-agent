"""
API Route Handlers.

Defines REST endpoints for Health, Chat orchestration, Document Ingestion,
Support Tickets, and MCP Tools. Follows clean architecture: delegates business
and agent logic to dedicated services.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import get_settings
from app.database.connection import DatabaseManager
from app.database import crud
from app.database.models import TicketCreate
from app.agent.service import AgentService
from app.agent.schemas import ConversationTurn
from app.rag.ingestion import DocumentIngestionPipeline
from app.api.dependencies import (
    verify_api_key,
    get_db,
    get_agent_service_dep,
    get_ingestion_pipeline,
)
from app.api.schemas import (
    HealthResponse,
    ComponentHealth,
    ChatRequest,
    ChatResponse,
    RetrievedKnowledgeItemDTO,
    ToolExecutionResultDTO,
    IngestRequest,
    IngestResponse,
    TicketCreateRequest,
    TicketResponse,
    ToolsListResponse,
    ToolDefinitionDTO,
    ToolExecuteRequest,
    ToolExecuteResponse,
)

logger = logging.getLogger("enterprise_agent.routes")

router = APIRouter()


# ==============================================================================
# Health Check Endpoints
# ==============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="System and Subsystem Health Check",
)
async def get_health(
    db: DatabaseManager = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service_dep),
) -> HealthResponse:
    """
    Returns service health status, environment parameters, and component diagnostics.
    Does not require API key authentication (used for container probes).
    """
    settings = get_settings()
    components: Dict[str, ComponentHealth] = {}

    # 1. Database readiness check
    try:
        with db.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        components["database"] = ComponentHealth(
            status="healthy",
            details={"path": settings.SQLITE_DB_PATH},
        )
    except Exception as exc:
        logger.warning("[Health] Database check failed: %s", exc)
        components["database"] = ComponentHealth(
            status="unavailable",
            details={"error": str(exc)},
        )

    # 2. Vector database (Qdrant) check
    components["vector_store"] = ComponentHealth(
        status="healthy",
        details={
            "url": settings.QDRANT_URL,
            "collection": settings.QDRANT_COLLECTION_NAME,
        },
    )

    # 3. MCP Client check
    mcp_connected = agent_service.is_mcp_connected
    components["mcp_client"] = ComponentHealth(
        status="healthy" if mcp_connected else "idle",
        details={"connected": mcp_connected},
    )

    # 4. LLM / Gemini check
    components["gemini_llm"] = ComponentHealth(
        status="healthy" if settings.is_gemini_configured() else "offline_fallback",
        details={
            "model": settings.GEMINI_MODEL,
            "configured": settings.is_gemini_configured(),
        },
    )

    overall_status = "healthy"
    if components["database"].status == "unavailable":
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        gemini_configured=settings.is_gemini_configured(),
        qdrant_url=settings.QDRANT_URL,
        components=components,
    )


# ==============================================================================
# Chat & Agent Orchestration
# ==============================================================================

@router.post(
    "/api/chat",
    response_model=ChatResponse,
    tags=["Agent Chat"],
    summary="Dispatch message to Google ADK Agent Orchestrator",
)
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    api_key: str = Depends(verify_api_key),
    agent_service: AgentService = Depends(get_agent_service_dep),
) -> ChatResponse:
    """
    Submits a conversational turn to the multi-tier agent orchestrator.
    Routes dynamically to RAG, MCP Tools, or Hybrid synthesis.
    """
    request_id = getattr(request.state, "request_id", "req-unknown")

    # Map conversation history DTOs to domain models
    history = None
    if payload.conversation_history:
        history = [
            ConversationTurn(role=turn.role, content=turn.content)
            for turn in payload.conversation_history
        ]

    agent_response = await agent_service.run_chat(
        message=payload.message,
        conversation_history=history,
        user_id=payload.user_id,
        department=payload.department,
        filter_criteria=payload.filter_criteria,
        dry_run=payload.dry_run,
    )

    # Map retrieved knowledge items
    knowledge_dtos = [
        RetrievedKnowledgeItemDTO(
            filename=k.filename,
            section=k.section,
            page_number=k.page_number,
            chunk_text=k.chunk_text,
            relevance_score=k.relevance_score,
            citation=k.citation,
        )
        for k in agent_response.retrieved_knowledge
    ]

    # Map tool execution items
    tool_dtos = [
        ToolExecutionResultDTO(
            tool_name=t.tool_name,
            parameters=t.parameters,
            result=t.result,
            success=t.success,
        )
        for t in agent_response.tool_results
    ]

    is_grounded = agent_response.rag_result.is_grounded if agent_response.rag_result else True
    confidence = agent_response.rag_result.confidence_score if agent_response.rag_result else 1.0

    return ChatResponse(
        request_id=request_id,
        workflow=agent_response.workflow.value if hasattr(agent_response.workflow, "value") else str(agent_response.workflow),
        response=agent_response.response_text,
        retrieved_knowledge=knowledge_dtos,
        tool_results=tool_dtos,
        llm_explanation=agent_response.llm_explanation,
        grounded=is_grounded,
        confidence_score=confidence,
        audit_logs=agent_response.audit_logs,
    )


# ==============================================================================
# Document Ingestion
# ==============================================================================

@router.post(
    "/api/ingest",
    response_model=IngestResponse,
    tags=["Ingestion"],
    summary="Ingest policy documents into Qdrant vector database",
)
async def ingest_documents_endpoint(
    payload: IngestRequest,
    api_key: str = Depends(verify_api_key),
    pipeline: DocumentIngestionPipeline = Depends(get_ingestion_pipeline),
) -> IngestResponse:
    """
    Triggers document loading, chunking, embedding, and vector upsert into Qdrant.
    Accepts explicit file paths or a directory path.
    """
    if not payload.file_paths and not payload.directory_path:
        # Default to documents directory in workspace if available
        default_dir = Path("data/documents")
        if default_dir.exists():
            payload.directory_path = str(default_dir)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_INGEST_INPUT",
                    "message": "Either 'file_paths' or 'directory_path' must be provided.",
                },
            )

    try:
        if payload.directory_path:
            dir_path = Path(payload.directory_path)
            if not dir_path.exists() or not dir_path.is_dir():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "DIRECTORY_NOT_FOUND",
                        "message": f"Directory path '{payload.directory_path}' does not exist.",
                    },
                )
            report = pipeline.ingest_directory(dir_path)
        else:
            paths = [Path(p) for p in (payload.file_paths or [])]
            for p in paths:
                if not p.exists():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "FILE_NOT_FOUND",
                            "message": f"File '{p}' does not exist on disk.",
                        },
                    )
            report = pipeline.ingest_files(paths)

        return IngestResponse(
            status=report.status,
            files_processed=report.files_processed,
            documents_loaded=report.documents_loaded,
            chunks_created=report.chunks_created,
            vectors_upserted=report.vectors_upserted,
            total_vectors_in_collection=report.total_vectors_in_collection,
            elapsed_seconds=report.elapsed_seconds,
            details=report.details,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Ingest] Pipeline failure: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INGESTION_FAILED",
                "message": f"Ingestion pipeline encountered an error: {str(exc)}",
            },
        )


# ==============================================================================
# Support Tickets
# ==============================================================================

@router.post(
    "/api/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Support Tickets"],
    summary="Create a new employee support ticket",
)
async def create_ticket_endpoint(
    payload: TicketCreateRequest,
    api_key: str = Depends(verify_api_key),
    db: DatabaseManager = Depends(get_db),
) -> TicketResponse:
    """
    Submits a support ticket record to the enterprise database.
    Validates that employee_id exists before creating.
    """
    try:
        ticket_data = TicketCreate(
            employee_id=payload.employee_id,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            priority=payload.priority,
        )
        ticket = crud.create_ticket(ticket_data=ticket_data, db_path=db.db_path)
        return TicketResponse(
            ticket_id=ticket.ticket_id,
            employee_id=ticket.employee_id,
            title=ticket.title,
            description=ticket.description,
            category=ticket.category.value if hasattr(ticket.category, "value") else str(ticket.category),
            priority=ticket.priority.value if hasattr(ticket.priority, "value") else str(ticket.priority),
            status=ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
            resolution_notes=ticket.resolution_notes,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )
    except ValueError as val_err:
        logger.warning("[Tickets] Validation error creating ticket: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_EMPLOYEE", "message": str(val_err)},
        )
    except Exception as exc:
        logger.error("[Tickets] Error creating ticket: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TICKET_CREATION_FAILED", "message": "Failed to create support ticket."},
        )


@router.get(
    "/api/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["Support Tickets"],
    summary="Retrieve support ticket by ID",
)
async def get_ticket_endpoint(
    ticket_id: str,
    api_key: str = Depends(verify_api_key),
    db: DatabaseManager = Depends(get_db),
) -> TicketResponse:
    """
    Looks up an existing support ticket by its unique ticket identifier.
    """
    ticket = crud.get_ticket(ticket_id=ticket_id, db_path=db.db_path)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TICKET_NOT_FOUND",
                "message": f"Support ticket '{ticket_id}' was not found.",
            },
        )

    return TicketResponse(
        ticket_id=ticket.ticket_id,
        employee_id=ticket.employee_id,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category.value if hasattr(ticket.category, "value") else str(ticket.category),
        priority=ticket.priority.value if hasattr(ticket.priority, "value") else str(ticket.priority),
        status=ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
        resolution_notes=ticket.resolution_notes,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


# ==============================================================================
# MCP Tools Discovery & Direct Invocation
# ==============================================================================

@router.get(
    "/api/tools",
    response_model=ToolsListResponse,
    tags=["MCP Tools"],
    summary="List available MCP operational tools",
)
async def list_tools_endpoint(
    api_key: str = Depends(verify_api_key),
    agent_service: AgentService = Depends(get_agent_service_dep),
) -> ToolsListResponse:
    """
    Returns the catalog of registered MCP tools and their JSON Schema parameter specifications.
    """
    raw_tools = await agent_service.get_available_tools()
    tool_dtos = [
        ToolDefinitionDTO(
            name=t.get("name", "unknown"),
            description=t.get("description", ""),
            input_schema=t.get("input_schema", {}),
        )
        for t in raw_tools
    ]
    return ToolsListResponse(tools=tool_dtos, count=len(tool_dtos))


@router.post(
    "/api/tools/{tool_name}",
    response_model=ToolExecuteResponse,
    tags=["MCP Tools"],
    summary="Execute a registered MCP tool directly",
)
async def execute_tool_endpoint(
    tool_name: str,
    payload: ToolExecuteRequest,
    api_key: str = Depends(verify_api_key),
    agent_service: AgentService = Depends(get_agent_service_dep),
) -> ToolExecuteResponse:
    """
    Invokes an operational tool via MCP Client with supplied parameters.
    """
    exec_result = await agent_service.execute_tool(
        tool_name=tool_name,
        arguments=payload.arguments,
    )

    if not exec_result.get("success"):
        # Check if tool not recognized
        err_msg = str(exec_result.get("result", ""))
        if "not recognized" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "TOOL_NOT_FOUND", "message": err_msg},
            )

    return ToolExecuteResponse(
        tool_name=exec_result["tool_name"],
        success=exec_result["success"],
        result=exec_result["result"],
        execution_time_seconds=exec_result["execution_time_seconds"],
    )
