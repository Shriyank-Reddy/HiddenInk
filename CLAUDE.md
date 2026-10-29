# CLAUDE.md

**Goal:** HiddenInk scans PDF/DOCX resumes for hidden text/prompt injections aimed at AI screeners, explains each finding, and gives a Low/Medium/High risk score.

**Stack:** Python 3.11+, PyMuPDF, python-docx, reportlab (test data), scikit-learn (TF-IDF + logistic regression), Streamlit, matplotlib, pytest. No API keys, no network.

## Commands
```bash
pip install -r requirements.txt
python scripts/make_resumes.py && python -m hiddenink.evaluate main
python scripts/make_heldout.py && python -m hiddenink.evaluate heldout
python scripts/make_chart.py
streamlit run app/streamlit_app.py
python -m pytest -q
```

## File map
- `hiddenink/config.py` all thresholds; `models.py` dataclasses
- `extract_pdf.py`, `extract_docx.py` text spans + style + position + metadata
- `visibility.py` one check per hiding technique; `intent.py` + `intent_data.py` instruction detector
- `scoring.py` risk score and `scan(path)`; `evaluate.py` metrics (only module that reads labels)
- `scripts/` synthetic data generators + chart; `app/streamlit_app.py` UI; `tests/`; `docs/HOW_IT_WORKS.md`

## Rules
1. Keep it simple and readable; no new frameworks, Docker, DB or servers.
2. Synthetic data only: fictional names, `*.example` emails.
3. Detectors NEVER read label files (`data/labels.json`, `data/heldout_labels.json`); only `evaluate.py` does.
4. The held-out set is never used for tuning. If detectors, thresholds or intent training data change, regenerate a FRESH held-out set with new variations (edit `scripts/make_heldout.py`) and state which numbers are tuned vs held-out.
5. Intent training sentences (`intent_data.py`) must stay separate from every eval resume; held-out instructions must not appear in them.
