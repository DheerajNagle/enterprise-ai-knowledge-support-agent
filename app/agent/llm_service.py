"""
LLM Response Generation Service using Google ADK & Google GenAI SDK.

Handles grounded generation, citation verification, safe abstention for missing context,
and synthesis across knowledge retrieval and operational tool execution.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set
from google.adk.models.google_llm import Gemini
from app.config import get_settings
from app.agent.schemas import (
    AssembledContext,
    LLMExplanation,
    RetrievedKnowledgeItem,
    ToolExecutionResult,
)
from app.agent.prompts import (
    SYSTEM_INSTRUCTION,
    INSUFFICIENT_CONTEXT_MESSAGE,
    SECURITY_REFUSAL_MESSAGE,
)

logger = logging.getLogger("enterprise_agent.llm_service")

CITATION_PATTERN = re.compile(
    r"(?:Source:\s*\n?\s*([^\n\r,]+)\s*\n?\s*Section:\s*\n?\s*([^\n\r]+))|"
    r"(?:\[Source:\s*([^,\]]+)(?:,\s*Section:\s*([^,\]]+))?(?:,\s*Page\s*(\d+))?\])",
    re.IGNORECASE,
)


class LLMService:
    """
    Enterprise LLM generation service adhering to Google ADK and GenAI standards.

    Guarantees:
    - Zero hardcoded credentials (loads strictly from environment).
    - Grounded generation strictly anchored in retrieved documentation.
    - Honest abstention when context has insufficient evidence.
    - Anti-hallucination citation validation against retrieved candidates.
    - Graceful offline fallback when live API keys are absent or services are degraded.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.gemini_model
        self.api_key = api_key or settings.gemini_api_key
        self._custom_client = client
        self._gemini_model: Optional[Gemini] = None

    @property
    def is_configured(self) -> bool:
        """Returns True if a live client or valid API key is available."""
        if self._custom_client is not None:
            return True
        return bool(self.api_key and self.api_key.strip())

    def get_client(self) -> Optional[Any]:
        """Returns the active GenAI client, instantiating one if needed."""
        if self._custom_client is not None:
            return self._custom_client

        if not self.is_configured:
            return None

        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            return client
        except Exception as exc:
            logger.warning("[LLMService] Failed to instantiate google.genai.Client: %s", exc)
            return None

    def get_adk_model(self) -> Gemini:
        """Returns the Google ADK Gemini model wrapper."""
        if self._gemini_model is None:
            client = self.get_client()
            if client is not None:
                self._gemini_model = Gemini(model=self.model_name, client=client)
            else:
                self._gemini_model = Gemini(model=self.model_name)
        return self._gemini_model

    # --------------------------------------------------------------------------
    # Citation Extraction & Anti-Hallucination Validation
    # --------------------------------------------------------------------------

    def extract_citations(self, text: str) -> List[str]:
        """Extracts all citation strings formatted in either block or inline style."""
        citations: List[str] = []
        for match in CITATION_PATTERN.finditer(text):
            f1, s1, f2, s2, _ = match.groups()
            filename = (f1 or f2 or "").strip()
            section = (s1 or s2 or "General").strip()
            if filename:
                citations.append(f"Source:\n{filename}\nSection:\n{section}")
        return citations

    def validate_citations(self, citations: List[str], allowed_filenames: Set[str]) -> List[str]:
        """Filters out citations referring to documents not present in retrieved context."""
        valid: List[str] = []
        for cit in citations:
            for allowed in allowed_filenames:
                if allowed.lower() in cit.lower():
                    valid.append(cit)
                    break
        return valid

    # --------------------------------------------------------------------------
    # Grounded RAG Answer Generation
    # --------------------------------------------------------------------------

    async def generate_grounded_rag_answer(
        self,
        query: str,
        assembled_context: AssembledContext,
    ) -> LLMExplanation:
        """
        Generates a grounded answer citing verified documentation.
        If context is insufficient, enforces honest abstention without calling LLM.
        """
        # 1. Missing / Insufficient Context Safeguard
        if not assembled_context.retrieved_documents:
            logger.info("[LLMService] Insufficient evidence for query: '%s'. Triggering abstention.", query)
            return LLMExplanation(
                text=INSUFFICIENT_CONTEXT_MESSAGE,
                model_name=self.model_name,
                grounded=False,
                confidence_score=0.0,
                citations=[],
            )

        # 2. Safety Refusal Safeguard
        if assembled_context.query_analysis.is_potential_injection:
            logger.warning("[LLMService] Potential injection detected. Triggering security refusal.")
            return LLMExplanation(
                text=SECURITY_REFUSAL_MESSAGE,
                model_name=self.model_name,
                grounded=True,
                confidence_score=1.0,
                citations=[],
            )

        allowed_filenames = {doc.filename for doc in assembled_context.retrieved_documents}

        # 3. Construct Grounded Prompt
        prompt = self._build_rag_prompt(query, assembled_context)

        # 4. Attempt Live Gemini Generation
        generated_text = await self._call_llm_async(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION)

        if generated_text:
            raw_citations = self.extract_citations(generated_text)
            validated_citations = self.validate_citations(raw_citations, allowed_filenames)

            # Ensure citations exist if factual claims were made
            if not validated_citations and assembled_context.source_metadata:
                top_source = assembled_context.source_metadata[0]
                formatted_citation = f"Source:\n{top_source.filename}\nSection:\n{top_source.section}"
                validated_citations.append(formatted_citation)
                if "Source:" not in generated_text:
                    generated_text += f"\n\n{formatted_citation}"

            return LLMExplanation(
                text=generated_text.strip(),
                model_name=self.model_name,
                grounded=True,
                confidence_score=round(assembled_context.retrieved_documents[0].priority_score, 4),
                citations=validated_citations,
            )

        # 5. Deterministic Grounded Fallback (when offline or API unavailable)
        logger.info("[LLMService] Using deterministic grounded synthesis fallback.")
        top_chunk = assembled_context.retrieved_documents[0]
        fallback_parts = [
            f"Based on the official enterprise policy ({top_chunk.filename}, Section: {top_chunk.section}):\n",
            f"{top_chunk.text}\n",
        ]
        if len(assembled_context.retrieved_documents) > 1:
            sec_chunk = assembled_context.retrieved_documents[1]
            fallback_parts.append(
                f"\nAdditional Policy Provisions ({sec_chunk.filename}, Section: {sec_chunk.section}):\n{sec_chunk.text}\n"
            )

        citations: List[str] = []
        fallback_parts.append("\nSources:")
        for meta in assembled_context.source_metadata:
            cit_str = f"Source:\n{meta.filename}\nSection:\n{meta.section}"
            bracketed_cit = f"[Source: {meta.filename}, Section: {meta.section}]"
            citations.append(cit_str)
            fallback_parts.append(f"\n{bracketed_cit}\n\n{cit_str}\n")

        return LLMExplanation(
            text="".join(fallback_parts).strip(),
            model_name="grounded-deterministic-fallback",
            grounded=True,
            confidence_score=round(top_chunk.priority_score, 4),
            citations=citations,
        )

    # --------------------------------------------------------------------------
    # Tool Execution Explanation Generation
    # --------------------------------------------------------------------------

    async def generate_tool_explanation(
        self,
        query: str,
        tool_result: ToolExecutionResult,
    ) -> LLMExplanation:
        """
        Generates a clear natural language explanation of an operational tool execution.
        """
        if not tool_result.success:
            err_msg = (
                f"I was unable to complete the requested action using `{tool_result.tool_name}`: "
                f"{tool_result.result}. Please verify your parameters or contact an administrator."
            )
            return LLMExplanation(
                text=err_msg,
                model_name=self.model_name,
                grounded=True,
                confidence_score=1.0,
                citations=[],
            )

        prompt = (
            f"User Inquiry: {query}\n\n"
            f"Tool Executed: {tool_result.tool_name}\n"
            f"Tool Parameters: {tool_result.parameters}\n"
            f"Execution Output: {tool_result.result}\n\n"
            "Provide a concise, professional, and helpful confirmation explaining the action taken, "
            "highlighting key IDs or status values, and outlining any follow-up steps for the employee."
        )

        explanation_text = await self._call_llm_async(
            prompt=prompt,
            system_instruction="You are an enterprise support agent confirming an action taken on behalf of an employee.",
        )

        if not explanation_text:
            # Deterministic fallback
            r = tool_result.result
            if tool_result.tool_name == "create_support_ticket" and isinstance(r, dict):
                explanation_text = (
                    f"Your support ticket **{r.get('ticket_id', 'TCK-UNKNOWN')}** has been successfully created "
                    f"with priority **{r.get('priority', 'MEDIUM')}** under the **{r.get('category', 'IT')}** category. "
                    f"Our support engineering team will review it shortly."
                )
            elif tool_result.tool_name == "get_ticket_status" and isinstance(r, dict):
                explanation_text = (
                    f"Support ticket **{r.get('ticket_id')}** is currently **{r.get('status')}** "
                    f"(Priority: {r.get('priority')}, Category: {r.get('category')}). Title: \"{r.get('title')}\"."
                )
            elif tool_result.tool_name == "get_employee_info" and isinstance(r, dict):
                explanation_text = (
                    f"Employee record found for **{r.get('name')}** (ID: {r.get('employee_id')}, "
                    f"Department: {r.get('department')}, Role: {r.get('role')}, Email: {r.get('email')})."
                )
            else:
                explanation_text = f"Action `{tool_result.tool_name}` was successfully executed: {tool_result.result}"

        return LLMExplanation(
            text=explanation_text.strip(),
            model_name=self.model_name,
            grounded=True,
            confidence_score=1.0,
            citations=[],
        )

    # --------------------------------------------------------------------------
    # Hybrid (Policy + Action) Explanation Generation
    # --------------------------------------------------------------------------

    async def generate_hybrid_explanation(
        self,
        query: str,
        assembled_context: AssembledContext,
        tool_result: ToolExecutionResult,
    ) -> LLMExplanation:
        """
        Synthesizes a combined explanation evaluating policy compliance and confirming action taken.
        """
        allowed_filenames = {doc.filename for doc in assembled_context.retrieved_documents}

        prompt = (
            f"User Inquiry: {query}\n\n"
            f"Retrieved Policy Context:\n{assembled_context.rendered_prompt}\n\n"
            f"Operational Tool Executed: {tool_result.tool_name}\n"
            f"Tool Parameters: {tool_result.parameters}\n"
            f"Tool Execution Result: {tool_result.result}\n\n"
            "Instructions:\n"
            "1. Explain the relevant policy provisions and cite the exact source using:\n"
            "   Source:\n   <filename>\n   Section:\n   <section>\n"
            "2. Explain the action taken and its status.\n"
            "3. State clearly how the action connects to the policy evaluation."
        )

        explanation_text = await self._call_llm_async(
            prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
        )

        if explanation_text:
            raw_citations = self.extract_citations(explanation_text)
            validated_citations = self.validate_citations(raw_citations, allowed_filenames)
            if not validated_citations and assembled_context.source_metadata:
                top_source = assembled_context.source_metadata[0]
                formatted = f"Source:\n{top_source.filename}\nSection:\n{top_source.section}"
                validated_citations.append(formatted)
                if "Source:" not in explanation_text:
                    explanation_text += f"\n\n{formatted}"

            return LLMExplanation(
                text=explanation_text.strip(),
                model_name=self.model_name,
                grounded=True,
                confidence_score=1.0,
                citations=validated_citations,
            )

        # Deterministic fallback
        top_chunk = assembled_context.retrieved_documents[0] if assembled_context.retrieved_documents else None
        citations: List[str] = []
        policy_summary = "Policy evaluated against corporate guidelines."
        if top_chunk:
            cit_str = f"Source:\n{top_chunk.filename}\nSection:\n{top_chunk.section}"
            citations.append(cit_str)
            policy_summary = (
                f"Based on the {top_chunk.filename} (Section: {top_chunk.section}):\n"
                f"{top_chunk.text}\n\n"
                f"{cit_str}"
            )

        action_summary = f"Action `{tool_result.tool_name}` successfully completed: {tool_result.result}"
        if isinstance(tool_result.result, dict) and "ticket_id" in tool_result.result:
            action_summary = (
                f"Support ticket **{tool_result.result.get('ticket_id')}** has been created "
                f"with priority **{tool_result.result.get('priority', 'MEDIUM')}**."
            )

        combined_text = (
            f"### Policy Evaluation\n{policy_summary}\n\n"
            f"### Action Taken\n{action_summary}"
        )

        return LLMExplanation(
            text=combined_text,
            model_name="grounded-deterministic-fallback",
            grounded=True,
            confidence_score=1.0,
            citations=citations,
        )

    # --------------------------------------------------------------------------
    # Internal Async LLM Invocation
    # --------------------------------------------------------------------------

    async def _call_llm_async(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Optional[str]:
        """Calls Gemini model asynchronously with error handling and fallback."""
        client = self.get_client()
        if client is None:
            return None

        try:
            # Check if client has aio (official google.genai.Client)
            if hasattr(client, "aio") and hasattr(client.aio, "models"):
                config: Dict[str, Any] = {"temperature": 0.2}
                if system_instruction:
                    config["system_instruction"] = system_instruction

                response = await client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()

            # Synchronous client fallback
            if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                config = {"temperature": 0.2}
                if system_instruction:
                    config["system_instruction"] = system_instruction
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()

        except Exception as exc:
            logger.warning("[LLMService] Gemini API call failed: %s", exc)

        return None

    def _build_rag_prompt(self, query: str, context: AssembledContext) -> str:
        """Constructs prompt enforcing grounding and strict citation format."""
        docs_text = "\n\n".join(
            f"--- Document: {d.filename} | Section: {d.section} ---\n{d.text}"
            for d in context.retrieved_documents
        )

        prompt = f"""You are the Enterprise AI Knowledge Agent answering an employee inquiry.

### STRICT CITATION REQUIREMENTS:
1. Use ONLY the factual information directly stated in the Retrieved Documents below.
2. Never extrapolate, guess, or incorporate external corporate rules.
3. Every factual sentence or policy statement MUST include a citation formatted EXACTLY as:
Source:
<filename>
Section:
<section>
4. Do NOT fabricate or cite documents not present in the Retrieved Documents.
5. If the documents do not provide enough evidence, state that the information is unavailable.

### RETRIEVED DOCUMENTS:
{docs_text}

### USER INQUIRY:
{query}

Provide a well-structured, professional, and strictly cited answer:
"""
        return prompt
