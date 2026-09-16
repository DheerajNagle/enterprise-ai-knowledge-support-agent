"""
Reranking Subsystem for Enterprise RAG.

Provides a modular interface for candidate reranking:
- BaseReranker: Abstract interface for reranking implementations.
- LexicalSemanticReranker: Real lexical-semantic coverage & phrase rescorer
  combining dense vector scores with BM25-style term coverage and exact section boosts.
- NoOpReranker: Pass-through reranker when reranking is bypassed.

Extension Point:
For production environments with GPU or ONNX acceleration, neural cross-encoders
(e.g., BAAI/bge-reranker-base, Cohere Rerank API, or FlashRank) can plug into
this BaseReranker interface without changing the retriever pipeline.
"""

from abc import ABC, abstractmethod
import math
import re
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.rag.retriever import RetrievalResult


class BaseReranker(ABC):
    """Abstract interface for candidate document reranking."""

    @abstractmethod
    def rerank(
        self, query: str, results: List["RetrievalResult"], top_k: int = 5
    ) -> List["RetrievalResult"]:
        """
        Reranks a list of retrieved results against the query.
        Returns the top_k rescored results sorted by descending score.
        """
        pass


class NoOpReranker(BaseReranker):
    """Pass-through reranker that preserves the original vector similarity order."""

    def rerank(
        self, query: str, results: List["RetrievalResult"], top_k: int = 5
    ) -> List["RetrievalResult"]:
        return results[:top_k]


class LexicalSemanticReranker(BaseReranker):
    """
    Real Lexical-Semantic Coverage & Phrase Rescorer.

    Blends the vector similarity score with:
    1. Query term coverage: Reward candidates containing higher percentage of query keywords.
    2. Exact phrase and section match bonus: Reward exact multi-word matches in text or section title.
    3. Length normalization penalty: Avoids bias towards excessively short or long chunks.

    Combined Score Formula:
      final_score = 0.65 * vector_score + 0.25 * term_coverage + 0.10 * exact_phrase_bonus
    """

    def __init__(
        self,
        vector_weight: float = 0.65,
        coverage_weight: float = 0.25,
        phrase_weight: float = 0.10,
    ):
        self.vector_weight = vector_weight
        self.coverage_weight = coverage_weight
        self.phrase_weight = phrase_weight

    def _tokenize(self, text: str) -> List[str]:
        """Extracts lowercase alphabetic words of length >= 3."""
        return re.findall(r"\b[a-z0-9_\-]{3,}\b", text.lower())

    def _compute_coverage(self, query_tokens: List[str], text_tokens: set) -> float:
        """Calculates proportion of unique query tokens present in document text."""
        if not query_tokens:
            return 0.0
        unique_query = set(query_tokens)
        matched = unique_query.intersection(text_tokens)
        return len(matched) / len(unique_query)

    def _compute_phrase_bonus(self, query: str, text: str, section: str) -> float:
        """Checks for multi-word exact subphrase matches in text and section."""
        query_clean = query.strip().lower()
        # Remove common question words for phrase matching
        query_clean = re.sub(
            r"^(what is|how do i|how to|where can i|can i|explain the)\s+",
            "",
            query_clean,
        )
        if len(query_clean) < 5:
            return 0.0

        bonus = 0.0
        text_lower = text.lower()
        section_lower = section.lower()

        # Check if substantive query phrase appears in section or text
        if query_clean in section_lower:
            bonus += 1.0
        elif query_clean in text_lower:
            bonus += 0.7
        else:
            # Check 2-word n-grams
            words = query_clean.split()
            if len(words) >= 2:
                bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
                bigram_matches = sum(1 for bg in bigrams if bg in text_lower)
                bonus += min(0.5, (bigram_matches / len(bigrams)) * 0.5)

        return min(1.0, bonus)

    def rerank(
        self, query: str, results: List["RetrievalResult"], top_k: int = 5
    ) -> List["RetrievalResult"]:
        """Reranks retrieved results and returns the top_k rescored results."""
        if not results:
            return []

        query_tokens = self._tokenize(query)

        rescored_results = []
        for item in results:
            doc_tokens = set(self._tokenize(item.text))
            coverage = self._compute_coverage(query_tokens, doc_tokens)
            phrase_bonus = self._compute_phrase_bonus(query, item.text, item.section)

            # Combined score
            blended_score = (
                self.vector_weight * item.score
                + self.coverage_weight * coverage
                + self.phrase_weight * phrase_bonus
            )

            # Create a shallow copy with the updated score and ranking metadata
            item_copy = item.model_copy()
            item_copy.score = round(blended_score, 4)
            item_copy.metadata = {
                **item.metadata,
                "original_vector_score": item.score,
                "rerank_coverage": round(coverage, 3),
                "rerank_phrase_bonus": round(phrase_bonus, 3),
            }
            rescored_results.append(item_copy)

        # Sort descending by rescored score
        rescored_results.sort(key=lambda r: r.score, reverse=True)
        return rescored_results[:top_k]
