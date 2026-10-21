"""Promptify Retrieval Evaluation Script

Calculates Recall@3, Recall@5, and Mean Reciprocal Rank (MRR) across curated evaluation vibe queries.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def evaluate_retrieval_dataset(vector_store, dataset_path=None, k_values=(3, 5)):
    """Run retrieval evaluation against ground-truth dataset and compute metrics."""
    if dataset_path is None:
        dataset_path = Path(__file__).resolve().parent / "tests" / "data" / "retrieval_eval_cases.json"
    
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    cases = data.get("cases", [])
    if not cases:
        print("No evaluation cases found in dataset.")
        return {}

    max_k = max(k_values)
    recalls = {k: [] for k in k_values}
    reciprocal_ranks = []
    case_results = []

    for case in cases:
        query = case["query"]
        expected = set(case.get("expected_snippets", []))
        
        # Retrieve top max_k results
        results = vector_store.similarity_search(query, k=max_k)
        retrieved_texts = [r.page_content if hasattr(r, "page_content") else str(r) for r in results]
        
        # Calculate Recall@k: fraction of expected snippets found in top k
        case_recalls = {}
        for k in k_values:
            top_k_retrieved = set(retrieved_texts[:k])
            hits = len(top_k_retrieved.intersection(expected))
            recall_k = hits / len(expected) if expected else 0.0
            recalls[k].append(recall_k)
            case_recalls[k] = recall_k

        # Calculate Reciprocal Rank: 1 / rank of first relevant item
        rr = 0.0
        for rank, text in enumerate(retrieved_texts, 1):
            if text in expected:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        case_results.append({
            "id": case["id"],
            "query": query,
            "category": case.get("category", ""),
            "recalls": case_recalls,
            "rr": rr,
            "first_match": retrieved_texts[0] if retrieved_texts else None
        })

    avg_recalls = {f"Recall@{k}": sum(recalls[k]) / len(recalls[k]) for k in k_values}
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0

    metrics = {
        "total_cases": len(cases),
        "MRR": round(mrr, 4),
        **{k: round(v, 4) for k, v in avg_recalls.items()},
        "case_results": case_results
    }
    return metrics

def print_evaluation_report(metrics):
    """Print formatted evaluation report to stdout."""
    print("=" * 65)
    print("        PROMPTIFY RETRIEVAL EVALUATION REPORT")
    print("=" * 65)
    print(f"Total Evaluated Cases: {metrics.get('total_cases', 0)}")
    print(f"Mean Reciprocal Rank (MRR): {metrics.get('MRR', 0.0):.4f}")
    for k in [3, 5]:
        key = f"Recall@{k}"
        if key in metrics:
            print(f"{key}: {metrics[key]:.4f} ({metrics[key]*100:.1f}%)")
    print("-" * 65)
    print(f"{'Case ID':<10} | {'Category':<22} | {'MRR':<6} | {'Recall@3':<8} | {'Top Match'}")
    print("-" * 65)
    for c in metrics.get("case_results", []):
        top = c["first_match"][:20] + "..." if c["first_match"] and len(c["first_match"]) > 20 else str(c["first_match"])
        print(f"{c['id']:<10} | {c['category']:<22} | {c['rr']:<6.2f} | {c['recalls'].get(3, 0):<8.2f} | {top}")
    print("=" * 65)

if __name__ == "__main__":
    from vibe_agent import get_vector_store, get_google_api_key
    try:
        get_google_api_key()
    except ValueError as e:
        print(f"Error: {e}")
        print("Set GOOGLE_API_KEY in your .env to run live evaluation.")
        sys.exit(1)

    print("Initializing FAISS vector store...")
    store = get_vector_store()
    print("Running evaluation on ground truth queries...")
    results = evaluate_retrieval_dataset(store)
    print_evaluation_report(results)
