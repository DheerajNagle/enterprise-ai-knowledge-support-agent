"""
Agent & Prompt Engineering Package.

Exports structured, versioned prompt templates, builder utilities,
and operational policies for the Enterprise AI Knowledge & Support Agent.
"""

from app.agent.prompts import (
    PROMPT_VERSIONS,
    SYSTEM_INSTRUCTION,
    RAG_ANSWER_TEMPLATE,
    TOOL_USAGE_INSTRUCTION,
    GROUNDING_VERIFICATION_PROMPT,
    INSUFFICIENT_CONTEXT_MESSAGE,
    SECURITY_REFUSAL_MESSAGE,
    format_context_chunks,
    format_conversation_history,
    build_system_prompt,
    build_rag_prompt,
    build_tool_instruction,
    build_grounding_eval_prompt,
    build_refusal_response,
)
from app.agent.schemas import (
    QueryAnalysis,
    ConversationTurn,
    ToolResultItem,
    SourceMetadataItem,
    PrioritizedChunk,
    AssembledContext,
)
from app.agent.context import (
    ContextEngine,
    estimate_tokens,
    extract_keywords,
)
from app.agent.rag_agent import RAGAgent, RAGAgentResult
from app.agent.tool_agent import MCPToolAgent, ToolAgentResult
from app.agent.root_agent import RootAgent, WorkflowType, AgentResponse

__all__ = [
    # Prompts
    "PROMPT_VERSIONS",
    "SYSTEM_INSTRUCTION",
    "RAG_ANSWER_TEMPLATE",
    "TOOL_USAGE_INSTRUCTION",
    "GROUNDING_VERIFICATION_PROMPT",
    "INSUFFICIENT_CONTEXT_MESSAGE",
    "SECURITY_REFUSAL_MESSAGE",
    "format_context_chunks",
    "format_conversation_history",
    "build_system_prompt",
    "build_rag_prompt",
    "build_tool_instruction",
    "build_grounding_eval_prompt",
    "build_refusal_response",
    # Context Schemas
    "QueryAnalysis",
    "ConversationTurn",
    "ToolResultItem",
    "SourceMetadataItem",
    "PrioritizedChunk",
    "AssembledContext",
    # Context Engine
    "ContextEngine",
    "estimate_tokens",
    "extract_keywords",
    # Google ADK Agents
    "RootAgent",
    "RAGAgent",
    "MCPToolAgent",
    "WorkflowType",
    "AgentResponse",
    "RAGAgentResult",
    "ToolAgentResult",
]
