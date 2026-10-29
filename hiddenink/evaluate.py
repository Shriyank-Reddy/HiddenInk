"""Evaluate the detector against a labels file. The ONLY module that reads labels.

Usage:  python -m hiddenink.evaluate main      -> results/results.json
        python -m hiddenink.evaluate heldout   -> results/heldout_results.json
"""
import json
import sys
from pathlib import Path

from .scoring import scan

ROOT = Path(__file__).resolve().parent.parent
TECHNIQUES = ["low_contrast", "tiny_font", "off_page", "covered_by_shape", "docx_vanish", "metadata", "zero_width"]
SETS = {"main": ("data/labels.json", "results/results.json"),
        "heldout": ("data/heldout_labels.json", "results/heldout_results.json")}


def _safe_div(a, b):
    return round(a / b, 3) if b else None


def _metrics(tp, fp, fn, tn):
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": _safe_div(tp, tp + fp), "recall": _safe_div(tp, tp + fn),
            "false_positive_rate": _safe_div(fp, fp + tn)}


def _confusion(pairs):
    """pairs = [(actual_bool, predicted_bool), ...]"""
    tp = sum(a and p for a, p in pairs)
    fp = sum((not a) and p for a, p in pairs)
    fn = sum(a and (not p) for a, p in pairs)
    tn = sum((not a) and (not p) for a, p in pairs)
    return tp, fp, fn, tn


def evaluate(labels_path, data_root=ROOT / "data") -> dict:
    labels = json.loads(Path(labels_path).read_text())
    rows = []
    for lab in labels:
        result = scan(data_root / lab["file"])
        rows.append({"file": lab["file"], "label": lab,
                     "predicted_techniques": sorted({f.technique for f in result.findings}),
                     "score": result.score, "level": result.level,
                     "instruction_found": any(f.intent == "instruction" for f in result.findings)})

    # Document level: "manipulated" is predicted when the risk level is Medium or High.
    overall = _metrics(*_confusion([(r["label"]["manipulated"], r["level"] != "Low") for r in rows]))

    per_technique = {}
    for tech in TECHNIQUES:
        pairs = [(tech in r["label"]["techniques"], tech in r["predicted_techniques"]) for r in rows]
        if any(a or p for a, p in pairs):
            per_technique[tech] = _metrics(*_confusion(pairs))

    instr = [r for r in rows if r["label"]["kind"] == "instruction"]
    summary = {
        "n_documents": len(rows), "n_manipulated": sum(r["label"]["manipulated"] for r in rows),
        "overall": overall, "per_technique": per_technique,
        "instruction_recall": _safe_div(sum(r["instruction_found"] for r in instr), len(instr)),
        "missed": [r["file"] for r in rows if r["label"]["manipulated"] and r["level"] == "Low"],
        "false_alarms": [r["file"] for r in rows if not r["label"]["manipulated"] and r["level"] != "Low"],
        "documents": [{"file": r["file"], "actual": r["label"]["techniques"], "predicted": r["predicted_techniques"],
                       "score": r["score"], "level": r["level"]} for r in rows],
    }
    return summary


def main(which):
    labels_rel, out_rel = SETS[which]
    summary = evaluate(ROOT / labels_rel)
    (ROOT / out_rel).write_text(json.dumps(summary, indent=1))
    o = summary["overall"]
    print(f"[{which}] docs={summary['n_documents']} precision={o['precision']} recall={o['recall']} "
          f"FPR={o['false_positive_rate']}  missed={len(summary['missed'])} false_alarms={len(summary['false_alarms'])}")
    for tech, m in summary["per_technique"].items():
        print(f"   {tech:17s} P={m['precision']} R={m['recall']} FPR={m['false_positive_rate']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "main")
