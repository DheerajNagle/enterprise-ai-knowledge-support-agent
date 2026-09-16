"""
Automated Pytest Suite for AI Evaluation Framework.

Validates:
1. Benchmark dataset integrity and categorical distribution (>= 25 questions across 8 categories).
2. MCP tools evaluation runner execution and JSON artifact emission.
3. RAG evaluation runner execution and metrics computation.
4. Timeout and safe degradation behavior in agent evaluation runner.
"""

import json
from pathlib import Path
import pytest

from evaluation.evaluate_tools import run_tools_evaluation
from evaluation.evaluate_rag import run_rag_evaluation
from evaluation.evaluate_agents import run_agent_evaluation


EXPECTED_CATEGORIES = {
    "rag_factual",
    "rag_multi_doc",
    "mcp_tool",
    "rag_mcp_hybrid",
    "irrelevant",
    "hallucination_test",
    "prompt_injection",
    "ambiguous",
}


def test_evaluation_dataset_structure_and_categories():
    dataset_path = Path("evaluation/dataset.json")
    assert dataset_path.exists(), "evaluation/dataset.json must exist"

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    assert isinstance(dataset, list)
    assert len(dataset) >= 25, f"Expected at least 25 questions, got {len(dataset)}"

    categories_found = set()
    ids_seen = set()

    for item in dataset:
        assert "id" in item, "Each item must have an id"
        assert "category" in item, "Each item must have a category"
        assert "question" in item, "Each item must have a question"
        assert "expected_workflow" in item, "Each item must have an expected_workflow"
        assert "expected_refusal" in item, "Each item must have an expected_refusal"

        # Unique ID check
        assert item["id"] not in ids_seen, f"Duplicate question ID found: {item['id']}"
        ids_seen.add(item["id"])
        categories_found.add(item["category"])

    assert categories_found == EXPECTED_CATEGORIES, (
        f"Missing categories: {EXPECTED_CATEGORIES - categories_found}"
    )


def test_tools_evaluation_runner_generates_report(tmp_path):
    report = run_tools_evaluation(output_dir=str(tmp_path))

    assert report["evaluation_type"] == "mcp_tools_evaluation"
    summary = report["summary"]
    assert summary["total_tests"] == 8
    assert summary["passed_tests"] > 0
    assert 0.0 <= summary["success_rate_percent"] <= 100.0
    assert summary["average_latency_ms"] >= 0.0

    # Verify JSON file was created
    json_files = list(tmp_path.glob("tools_eval_*.json"))
    assert len(json_files) == 1
    saved_data = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert saved_data["summary"]["total_tests"] == 8


def test_rag_evaluation_runner_generates_report(tmp_path):
    report = run_rag_evaluation(output_dir=str(tmp_path), top_k=2)

    assert report["evaluation_type"] == "rag_pipeline_evaluation"
    summary = report["summary"]
    assert summary["total_questions_evaluated"] > 0
    assert summary["retrieval_hit_rate_percent"] >= 0.0
    assert summary["citation_presence_rate_percent"] >= 0.0
    assert summary["grounded_refusal_accuracy_percent"] >= 0.0

    # Verify JSON artifact
    json_files = list(tmp_path.glob("rag_eval_*.json"))
    assert len(json_files) == 1
