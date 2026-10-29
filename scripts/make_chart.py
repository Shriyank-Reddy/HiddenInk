"""Chart: main (tuned) vs held-out metrics. Run after both evaluations."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

R = Path(__file__).resolve().parent.parent / "results"
MAIN_COLOR, HELD_COLOR = "#2a6f97", "#e07a1f"


def bars(ax, labels, main_vals, held_vals, title):
    xs = range(len(labels))
    ax.bar([x - 0.2 for x in xs], main_vals, 0.4, label="Main (tuned)", color=MAIN_COLOR)
    ax.bar([x + 0.2 for x in xs], held_vals, 0.4, label="Held-out (never tuned)", color=HELD_COLOR)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.spines[["top", "right"]].set_visible(False)


def main():
    main_r = json.loads((R / "results.json").read_text())
    held_r = json.loads((R / "heldout_results.json").read_text())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5), gridspec_kw={"width_ratios": [1, 2]})
    keys = ["precision", "recall", "false_positive_rate"]
    bars(a1, ["Precision", "Recall", "False pos. rate"],
         [main_r["overall"][k] or 0 for k in keys], [held_r["overall"][k] or 0 for k in keys], "Overall (document level)")
    techs = [t for t in main_r["per_technique"] if t in held_r["per_technique"]]
    bars(a2, techs, [main_r["per_technique"][t]["recall"] or 0 for t in techs],
         [held_r["per_technique"][t]["recall"] or 0 for t in techs], "Recall per technique")
    h, l = a1.get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=2, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(R / "comparison.png", dpi=130)
    print("saved", R / "comparison.png")


if __name__ == "__main__":
    main()
