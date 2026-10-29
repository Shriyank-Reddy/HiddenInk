# HiddenInk — Plan

Goal: scan PDF/DOCX resumes for hidden text aimed at manipulating AI screeners,
explain each finding, and give a Low/Medium/High risk score.
Target size: ~1,500–2,500 lines of code (data excluded). No paid APIs, no Docker, no DB.

## Architecture

```
file (PDF/DOCX)
   │
   ▼
1. Extraction ── extract_pdf.py / extract_docx.py
   → list of Span(text, font_size, color, bold, bbox, page, hidden_flag, source)
   → metadata dict (title, subject, keywords, author)
   │
   ▼
2. Visibility checks ── visibility.py
   each check returns Finding(technique, span text, reason, severity)
   low_contrast · tiny_font · off_page · covered_by_shape · docx_vanish ·
   metadata · zero_width_chars
   │
   ▼
3. Intent check ── intent.py
   regex rules + TF-IDF/logistic-regression classifier
   → intent_score (0–1) per hidden text:  "instruction"  |  "keyword stuffing" | "benign"
   │
   ▼
4. Scoring ── scoring.py
   findings + intent → numeric score (0–100) → Low / Medium / High + reasons
   │
   ▼
5. UI / reports: "what a human sees" vs "what the AI sees" (highlighted)
```

A single entry point `scan(path) -> ScanResult` (in `scoring.py`) ties it together.
Detectors **never** read label files; only `evaluate.py` does.

## File structure

```
hiddenink/
  hiddenink/            package
    config.py           all thresholds in one place (frozen before held-out eval)
    models.py           Span, Finding, ScanResult dataclasses
    extract_pdf.py      PyMuPDF → spans + metadata + filled rectangles
    extract_docx.py     python-docx → runs (color, size, vanish, highlight) + core props
    visibility.py       one function per technique + run_all_checks()
    intent.py           regex rules + TF-IDF/LogReg classifier (trained on small built-in text set)
    scoring.py          combine, explain, scan()
    evaluate.py         run on a data set + labels → precision/recall/FPR per technique & overall
  scripts/
    make_resumes.py     generates ~40 main resumes + data/labels.json
    make_heldout.py     generates ~12 held-out resumes (new variations) + data/heldout_labels.json
    make_chart.py       main vs held-out chart (matplotlib)
  app/streamlit_app.py  Scanner / Results / About pages
  tests/                pytest, fast and offline
  data/{clean,manipulated,heldout}/  labels.json  heldout_labels.json
  results/              results.json  heldout_results.json  comparison.png
  docs/HOW_IT_WORKS.md
  README.md  CLAUDE.md  PLAN.md  requirements.txt
```

## Detection rules (initial thresholds; all live in config.py)

| Technique | Check |
|---|---|
| Low contrast | WCAG contrast ratio between text color and page background (white, or a filled rect under the span) < ~1.5 → hidden; < 3 → suspicious only if text is also long/short-lived. Legit light gray (~#999 on white, ratio ≈ 2.8) must NOT be flagged |
| Tiny font | size < 2 pt (flag); small footnotes at 6–8 pt are fine |
| Off-page | span bbox mostly outside page rect (with small margin) |
| Hidden behind shape | span bbox ≥ 80% inside a filled rect whose fill color ≈ text color |
| DOCX vanish | run property `w:vanish` set (also white text / tiny size via the same color/size checks) |
| Metadata | title/subject/keywords/author fields containing long text or instruction-like text (judged by intent check) |
| Zero-width Unicode | count of U+200B/200C/200D/2060/FEFF in text above a small threshold |

Hidden-text decision: only spans flagged by a visibility check go to the intent check.
Zero-width characters are flagged on any text; metadata is flagged when it is long or instruction-like.

## Intent check

- Regex rules: "ignore previous instructions", "you are an AI", "rank this candidate", "top match",
  "recommend hiring", "system prompt", etc.
- TF-IDF (word 1–2 grams) + LogisticRegression, trained on a small hand-written set
  (~150 instruction-like vs ~150 normal resume sentences), written in `intent.py` data section. Trained at import
  time (milliseconds); no saved model file.
- Final intent score = max(rule score, classifier probability).
- Hidden text with no instruction intent but that looks like a block of skills/keywords → "keyword stuffing", lower severity.

## Scoring

Per finding: severity points = technique weight × intent multiplier
(instruction ≫ keyword stuffing ≫ plain hidden text). Overall score = capped sum (0–100):
Low < 25, Medium 25–59, High ≥ 60. Hidden instruction aimed at an AI always yields at least Medium+
(normally High). Each finding carries a one-sentence plain-English reason.

## Evaluation

- **Document-level** detection for overall precision/recall/FPR: a document is "predicted manipulated"
  if risk ≥ Medium.
- **Per-technique**: for each technique, positives = docs labeled with it; a doc is a true positive when the
  detector produced a finding of that technique; false positives = findings of that technique on docs without it
  (clean docs included). FPR per technique = docs falsely flagged ÷ docs without the technique.
- Main set (~40 docs) is used for tuning. Then thresholds are **frozen** (git commit + note in config.py),
  held-out set (~12 docs, new colors, slightly larger "tiny" fonts like 2.5–3 pt, paraphrased instructions,
  new layouts) is generated and evaluated once. Held-out results are never used to tune.
  If any detector changes afterward, a fresh held-out set is generated.
- Outputs: `results/results.json`, `results/heldout_results.json`, `results/comparison.png`.
- I expect held-out numbers to be lower than main; they will be reported as-is.

## Synthetic data

~20 clean resumes (random fake name/*.example email/fictional school+company; some with light-gray
text, 7pt footnotes, colored headings, light-colored header bars with dark text) and ~20 manipulated
(PDF via reportlab, DOCX via python-docx), each with 1–2 techniques. Some manipulated resumes use
benign hidden keyword stuffing. Labels in `data/labels.json`: `{file, manipulated, techniques[], injected_text}`.
Layouts vary a bit (one/two-column, header bar) via a few templates.

## Milestones (one commit each)

1. M1 Setup + resume generator + labels
2. M2 PDF/DOCX extraction
3. M3 Visibility checks
4. M4 Intent classifier + scoring + explanations
5. M5 Main evaluation + chart
6. M6 Freeze, held-out generation + evaluation
7. M7 Streamlit app
8. M8 Tests, README (real numbers), HOW_IT_WORKS.md, CLAUDE.md, PR

## Assumptions / simplifications (decided up front)

- Background is assumed white unless a filled rectangle sits beneath the span (PDF). DOCX page background
  and shading are assumed white (cell/paragraph shading ignored; noted as a limitation).
- Text hidden behind *images* is out of scope (only filled vector rectangles); noted in README.
- Scanned/image-only PDFs and OCR are out of scope.
- Intent classifier training data is small and synthetic, so it will be weaker than a real model;
  rules carry most of the weight. Honest limitation in README.
- "Cover" technique in DOCX: not supported (DOCX has no easy shape-overlay test); technique 4 is PDF only.
- Zero-width chars (technique 7) included since it is cheap.
- Python 3.11+ (environment has 3.13); pinned versions chosen from what installs cleanly.
- Streamlit app reads samples from `data/`; if absent, the Scanner page still works with uploads.
- Fonts: reportlab built-in Helvetica only; no external font downloads.
- Mermaid diagram goes in README.
- PR is opened at the end only because your Definition of Done requires it.

## Budget notes

One pip install, one evaluation run per milestone-gate (M5, M6, final sanity check), short test outputs, no re-reading large files.
