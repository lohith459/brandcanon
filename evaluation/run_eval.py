import json
import os
import sys
from collections import defaultdict
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

# Ensure app is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.seed.seed_data import seed_canon_data
from app.models.canon import Rule, Fact
from app.engine.layer_a import run_layer_a_checks
from app.engine.layer_d import verify_and_ground_findings

def run_evaluation(corpus_path: str = "evaluation/corpus.json"):
    """
    Evaluates BrandCanon review engine against labelled test corpus.
    Calculates:
    - Precision & Recall per category
    - Overall Precision, Recall, and F1 score
    - Citation-Integrity Rate (% of findings properly cited and text-grounded)
    """
    if not os.path.exists(corpus_path):
        print(f"Error: Corpus file not found at {corpus_path}")
        return

    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    # In-memory test database
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        seed_canon_data(session)

        total_expected = 0
        total_detected = 0
        true_positives = 0
        citation_valid_count = 0
        all_findings_count = 0

        cat_stats = defaultdict(lambda: {"expected": 0, "detected": 0, "tp": 0})

        for item in corpus:
            text = item["text"]
            cat = item.get("category", "general")
            expected_ids = set(item.get("expected_rule_ids", []) + item.get("expected_fact_ids", []))
            total_expected += len(expected_ids)
            cat_stats[cat]["expected"] += len(expected_ids)

            raw = run_layer_a_checks(text, session, version_id=f"eval-{item['id']}")
            verified, dropped = verify_and_ground_findings(raw, text, session)

            detected_ids = set()
            for f in verified:
                all_findings_count += 1
                cid = f.rule_id or f.fact_id
                if cid:
                    detected_ids.add(cid)
                    # Citation integrity check: Valid DB record and grounded text
                    has_db_record = (session.get(Rule, cid) is not None) or (session.get(Fact, cid) is not None)
                    is_grounded = (not f.quoted_text and f.span_start == 0 and f.span_end == len(text)) or (f.quoted_text in text)
                    if has_db_record and is_grounded:
                        citation_valid_count += 1

            total_detected += len(detected_ids)
            cat_stats[cat]["detected"] += len(detected_ids)

            # Match true positives
            matched_tp = expected_ids.intersection(detected_ids)
            true_positives += len(matched_tp)
            cat_stats[cat]["tp"] += len(matched_tp)

        # Global metrics
        precision = (true_positives / total_detected) if total_detected > 0 else 1.0
        recall = (true_positives / total_expected) if total_expected > 0 else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        citation_rate = (citation_valid_count / all_findings_count) if all_findings_count > 0 else 1.0

        print("\n=======================================================")
        print("         BRANDCANON EVALUATION BENCHMARK RESULTS       ")
        print("=======================================================")
        print(f"Test Corpus Size:           {len(corpus)} labelled test pieces")
        print(f"Total Expected Violations:  {total_expected}")
        print(f"Total Detected Findings:    {total_detected}")
        print(f"True Positives:             {true_positives}")
        print(f"Overall Precision:          {precision * 100:.2f}%")
        print(f"Overall Recall:             {recall * 100:.2f}%")
        print(f"Overall F1 Score:           {f1 * 100:.2f}%")
        print(f"Citation-Integrity Rate:    {citation_rate * 100:.2f}% (Evidence-or-Silence)")
        print("-------------------------------------------------------")
        print(f"{'Category':<15} | {'Expected':<8} | {'Detected':<8} | {'Precision':<9} | {'Recall':<8}")
        print("-------------------------------------------------------")
        for c, s in sorted(cat_stats.items()):
            c_prec = (s["tp"] / s["detected"] * 100) if s["detected"] > 0 else 100.0
            c_rec = (s["tp"] / s["expected"] * 100) if s["expected"] > 0 else 100.0
            print(f"{c:<15} | {s['expected']:<8} | {s['detected']:<8} | {c_prec:>8.1f}% | {c_rec:>7.1f}%")
        print("=======================================================\n")

        return {
            "corpus_size": len(corpus),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "citation_integrity_rate": round(citation_rate, 4),
            "category_breakdown": {
                c: {
                    "precision": round((s["tp"] / s["detected"]), 4) if s["detected"] > 0 else 1.0,
                    "recall": round((s["tp"] / s["expected"]), 4) if s["expected"] > 0 else 1.0
                }
                for c, s in cat_stats.items()
            }
        }

if __name__ == "__main__":
    run_evaluation()
