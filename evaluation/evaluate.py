"""
FRONTLINE — Evaluation Module with Confidence Calibration
Compares triage output against ground truth labels.
Produces accuracy metrics, failure analysis, and confidence calibration analysis.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)

GROUND_TRUTH_PATH = Path(__file__).parent.parent / "evaluation" / "ground_truth.json"
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
CONFIDENCE_THRESHOLD_FILE = CONFIG_DIR / "confidence_threshold.json"


def load_ground_truth(path: Path = GROUND_TRUTH_PATH) -> Dict[str, dict]:
    """Returns dict keyed by message ID."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {item["id"]: item for item in data}


def save_confidence_threshold(threshold: float):
    """Save the confidence threshold to config file."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIDENCE_THRESHOLD_FILE, "w") as f:
            json.dump({"threshold": max(0.0, min(1.0, threshold))}, f, indent=2)
        logger.info(f"Saved confidence threshold {threshold} to {CONFIDENCE_THRESHOLD_FILE}")
    except OSError as e:
        logger.warning(f"Could not save confidence threshold: {e}")


def load_confidence_threshold() -> float:
    """Load the confidence threshold for needs_human decision from config.
    Falls back to 0.6 if file doesn't exist or contains invalid data."""
    try:
        if CONFIDENCE_THRESHOLD_FILE.exists():
            with open(CONFIDENCE_THRESHOLD_FILE, "r") as f:
                config = json.load(f)
                threshold = float(config.get("threshold", 0.6))
                # Ensure threshold is in valid range
                return max(0.0, min(1.0, threshold))
    except (ValueError, json.JSONDecodeError, OSError):
        pass
    return 0.6  # Default threshold


def calculate_confidence_calibration(results: List[dict], ground_truth: Dict[str, dict]) -> Dict:
    """
    Calculate confidence calibration metrics.

    Returns:
        {
            "reliability_calibration": {
                "bins": List[float],  # bin boundaries
                "accuracies": List[float],  # accuracy in each bin
                "confidences": List[float],  # avg confidence in each bin
                "counts": List[int],  # samples in each bin
                "ece": float,  # Expected Calibration Error
                "mce": float   # Maximum Calibration Error
            },
            "threshold_analysis": {
                "current_threshold": 0.6,
                "optimal_threshold": float,  # threshold that maximizes F1 for needs_human
                "current_f1": float,
                "optimal_f1": float
            }
        }
    """
    # Get labeled results
    labeled_results = [r for r in results if r["id"] in ground_truth]

    if not labeled_results:
        return {"error": "No labeled messages found in results."}

    # Extract confidence scores and correctness for needs_human prediction
    confidences = []
    needs_human_correct = []  # True if prediction matches ground truth

    for result in labeled_results:
        gt = ground_truth[result["id"]]
        confidence = result.get("confidence", 0.5)
        pred_needs_human = result.get("needs_human", False)
        true_needs_human = gt.get("expected_needs_human", False)

        confidences.append(confidence)
        needs_human_correct.append(pred_needs_human == true_needs_human)

    # Convert to numpy arrays for easier computation
    confidences = np.array(confidences)
    needs_human_correct = np.array(needs_human_correct, dtype=float)  # Convert bool to float (0.0 or 1.0)

    # Calculate reliability diagram (calibration curve)
    n_bins = 10
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(confidences, bins) - 1  # 0-indexed bins

    bin_accuracies = []
    bin_confidences = []
    bin_counts = []

    for i in range(n_bins):
        # Get samples in this bin
        in_bin = bin_indices == i
        if np.sum(in_bin) > 0:
            bin_accuracies.append(np.mean(needs_human_correct[in_bin]))
            bin_confidences.append(np.mean(confidences[in_bin]))
            bin_counts.append(np.sum(in_bin))
        else:
            bin_accuracies.append(0.0)
            bin_confidences.append(0.0)
            bin_counts.append(0)

    # Calculate Expected Calibration Error (ECE)
    # Weighted average of |accuracy - confidence| across bins
    total_samples = len(confidences)
    ece = np.sum([
        (count / total_samples) * abs(acc - conf)
        for acc, conf, count in zip(bin_accuracies, bin_confidences, bin_counts)
    ])

    # Calculate Maximum Calibration Error (MCE)
    mce = np.max([
        abs(acc - conf)
        for acc, conf in zip(bin_accuracies, bin_confidences)
        if conf > 0  # Only consider bins with samples
    ]) if any(c > 0 for c in bin_counts) else 0.0

    # Threshold analysis for needs_human decision
    # Try different thresholds and find the one that gives best F1 score
    # Note: In our system, needs_human is True when confidence < THRESHOLD (low confidence)
    thresholds = np.linspace(0, 1, 101)  # 0.00, 0.01, ..., 1.00
    f1_scores = []
    true_labels = [ground_truth[r["id"]]["expected_needs_human"] for r in labeled_results]

    for threshold in thresholds:
        # Predict needs_human = True if confidence < threshold
        predictions = np.array(confidences) < threshold
        truths = np.array(true_labels)

        # Calculate precision, recall, F1
        tp = np.sum(predictions & truths)
        fp = np.sum(predictions & ~truths)
        fn = np.sum(~predictions & truths)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        f1_scores.append(f1)

    # Find optimal threshold
    best_idx = np.argmax(f1_scores)
    optimal_threshold = thresholds[best_idx]
    best_f1 = f1_scores[best_idx]

    # Current F1 with threshold = 0.6
    current_threshold = 0.6
    current_predictions = np.array(confidences) < current_threshold
    current_tp = np.sum(current_predictions & np.array(true_labels))
    current_fp = np.sum(current_predictions & ~np.array(true_labels))
    current_fn = np.sum(~current_predictions & np.array(true_labels))
    current_precision = current_tp / (current_tp + current_fp) if (current_tp + current_fp) > 0 else 0
    current_recall = current_tp / (current_tp + current_fn) if (current_tp + current_fn) > 0 else 0
    current_f1 = 2 * current_precision * current_recall / (current_precision + current_recall) if (current_precision + current_recall) > 0 else 0

    return {
        "reliability_calibration": {
            "bins": bins.tolist(),
            "accuracies": [float(a) for a in bin_accuracies],
            "confidences": [float(c) for c in bin_confidences],
            "counts": [int(c) for c in bin_counts],
            "ece": float(ece),
            "mce": float(mce)
        },
        "threshold_analysis": {
            "current_threshold": current_threshold,
            "current_f1": float(current_f1),
            "optimal_threshold": float(optimal_threshold),
            "optimal_f1": float(best_f1),
            "improvement": float(best_f1 - current_f1)
        }
    }


def evaluate(results: list[dict], ground_truth: dict = None) -> dict:
    """
    Compares triage results against ground truth.

    Returns:
        {
          "total_labeled": int,
          "category_accuracy": float,
          "priority_accuracy": float,
          "needs_human_accuracy": float,
          "overall_accuracy": float,
          "failures": [...],
          "cost_summary": {...},
          "confidence_calibration": {...}  # NEW: Calibration analysis
        }
    """
    if ground_truth is None:
        ground_truth = load_ground_truth()

    labeled_results = [r for r in results if r["id"] in ground_truth]
    total = len(labeled_results)

    if total == 0:
        return {"error": "No labeled messages found in results."}

    cat_correct = 0
    pri_correct = 0
    human_correct = 0
    failures = []

    for r in labeled_results:
        gt = ground_truth[r["id"]]
        cat_ok = r.get("category") == gt.get("expected_category")
        pri_ok = r.get("priority") == gt.get("expected_priority")
        human_ok = r.get("needs_human") == gt.get("expected_needs_human")

        if cat_ok:
            cat_correct += 1
        if pri_ok:
            pri_correct += 1
        if human_ok:
            human_correct += 1

        if not (cat_ok and pri_ok and human_ok):
            failures.append({
                "id": r["id"],
                "text_preview": r.get("original_text", "")[:80],
                "expected_category": gt.get("expected_category"),
                "got_category": r.get("category"),
                "expected_priority": gt.get("expected_priority"),
                "got_priority": r.get("priority"),
                "expected_needs_human": gt.get("expected_needs_human"),
                "got_needs_human": r.get("needs_human"),
                "confidence": r.get("confidence"),
                "notes": gt.get("notes", ""),
            })

    # Cost & latency summary
    all_meta = [r.get("_meta", {}) for r in results]
    total_tokens = sum(m.get("total_tokens") or 0 for m in all_meta)
    avg_latency = (
        sum(m.get("latency_s") or 0 for m in all_meta) / len(all_meta)
        if all_meta else 0
    )

    # Rough cost estimate (GPT-4o-mini: $0.15/1M input, $0.60/1M output)
    input_tokens = sum(m.get("input_tokens") or 0 for m in all_meta)
    output_tokens = sum(m.get("output_tokens") or 0 for m in all_meta)
    estimated_cost_usd = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)

    # Calculate confidence calibration
    calibration_data = calculate_confidence_calibration(results, ground_truth)

    return {
        "total_labeled": total,
        "category_accuracy": round(cat_correct / total, 3),
        "priority_accuracy": round(pri_correct / total, 3),
        "needs_human_accuracy": round(human_correct / total, 3),
        "overall_accuracy": round((cat_correct + pri_correct + human_correct) / (total * 3), 3),
        "failures": failures,
        "cost_summary": {
            "total_messages_processed": len(results),
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "avg_latency_s": round(avg_latency, 3),
            "estimated_cost_usd": round(estimated_cost_usd, 4),
            "cost_per_message_usd": round(estimated_cost_usd / len(results), 5) if results else 0,
        },
        "confidence_calibration": calibration_data
    }


def update_confidence_threshold_from_evaluation(results: list[dict], min_improvement: float = 0.01) -> bool:
    """
    Evaluate results and optionally update the confidence threshold if improvement is significant.

    Args:
        results: List of triage results
        min_improvement: Minimum improvement in F1 score required to update threshold

    Returns:
        True if threshold was updated, False otherwise
    """
    ground_truth = load_ground_truth()
    calibration_data = calculate_confidence_calibration(results, ground_truth)

    if "threshold_analysis" not in calibration_data:
        return False

    threshold_analysis = calibration_data["threshold_analysis"]
    improvement = threshold_analysis["improvement"]

    if improvement >= min_improvement:
        optimal_threshold = threshold_analysis["optimal_threshold"]
        save_confidence_threshold(optimal_threshold)
        logger.info(f"Updated confidence threshold from {threshold_analysis['current_threshold']} to {optimal_threshold} "
                   f"(F1 improvement: {improvement:.3f})")
        return True
    else:
        logger.info(f"Not updating confidence threshold. Improvement ({improvement:.3f}) below minimum threshold ({min_improvement})")
        return False


def print_evaluation_report(metrics: dict):
    """Prints a human-readable evaluation report."""
    print("\n" + "=" * 60)
    print("  FRONTLINE — EVALUATION REPORT")
    print("=" * 60)
    print(f"  Labeled messages evaluated : {metrics.get('total_labeled', 0)}")
    print(f"  Category accuracy          : {metrics.get('category_accuracy', 0):.1%}")
    print(f"  Priority accuracy          : {metrics.get('priority_accuracy', 0):.1%}")
    print(f"  Needs-human accuracy       : {metrics.get('needs_human_accuracy', 0):.1%}")
    print(f"  Overall accuracy           : {metrics.get('overall_accuracy', 0):.1%}")

    cost = metrics.get("cost_summary", {})
    print(f"\n  Messages processed         : {cost.get('total_messages_processed', 0)}")
    print(f"  Total tokens used          : {cost.get('total_tokens', 'N/A')}")
    print(f"  Avg latency per message    : {cost.get('avg_latency_s', 0):.3f}s")
    print(f"  Estimated cost             : ${cost.get('estimated_cost_usd', 0):.4f}")
    print(f"  Cost per message           : ${cost.get('cost_per_message_usd', 0):.5f}")

    # Print calibration information if available
    if "confidence_calibration" in metrics:
        cal = metrics["confidence_calibration"]
        if "reliability_calibration" in cal:
            rel_cal = cal["reliability_calibration"]
            print(f"\n  Confidence Calibration:")
            print(f"    Expected Calibration Error (ECE): {rel_cal['ece']:.3f}")
            print(f"    Maximum Calibration Error (MCE): {rel_cal['mce']:.3f}")

        if "threshold_analysis" in cal:
            thresh_anal = cal["threshold_analysis"]
            print(f"\n  Threshold Analysis for needs_human (confidence < threshold):")
            print(f"    Current threshold (0.6) F1 score: {thresh_anal['current_f1']:.3f}")
            print(f"    Optimal threshold: {thresh_anal['optimal_threshold']:.3f}")
            print(f"    Optimal F1 score: {thresh_anal['optimal_f1']:.3f}")
            print(f"    Potential improvement: {thresh_anal['improvement']:.3f}")

    failures = metrics.get("failures", [])
    if failures:
        print(f"\n  Failures ({len(failures)} total):")
        print("  " + "-" * 56)
        for f in failures:
            print(f"  [{f['id']}] {f['text_preview'][:60]}...")
            if f["expected_category"] != f["got_category"]:
                print(f"    Category: expected={f['expected_category']}, got={f['got_category']}")
            if f["expected_priority"] != f["got_priority"]:
                print(f"    Priority: expected={f['expected_priority']}, got={f['got_priority']}")
            if f["expected_needs_human"] != f["got_needs_human"]:
                print(f"    Needs human: expected={f['expected_needs_human']}, got={f['got_needs_human']}")
    else:
        print("\n  ✓ All labeled messages correctly classified!")

    print("=" * 60 + "\n")


# Command-line interface for updating threshold
if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))

    from src.triage.processor import process_all

    if len(sys.argv) > 1 and sys.argv[1] == "--update-threshold":
        print("Updating confidence threshold based on latest evaluation...")
        results = process_all()
        updated = update_confidence_threshold_from_evaluation(results)
        if updated:
            print("✓ Threshold updated successfully")
        else:
            print("✗ Threshold not updated (insufficient improvement)")
    else:
        print("Usage: python evaluate.py --update-threshold")
        print("       (Run evaluation and update confidence threshold if improvement is significant)")