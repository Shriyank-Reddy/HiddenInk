"""Combine visibility findings + intent into a risk score, and expose scan(path)."""
from . import config as cfg
from .extract_docx import extract
from .intent import analyze_intent
from .models import ScanResult
from .visibility import run_all_checks

INTENT_SENTENCE = {
    "instruction": "The hidden text reads like an instruction aimed at an AI screener (e.g. 'rank me first').",
    "keyword_stuffing": "The hidden text is a block of skill keywords, probably added to game keyword matching.",
    "other": "The hidden text does not look like an instruction, but a recruiter should still know it is there.",
}


def risk_level(score: int) -> str:
    return "High" if score >= cfg.HIGH_AT else "Medium" if score >= cfg.MEDIUM_AT else "Low"


def score_findings(findings) -> int:
    """Biggest finding counts fully; each extra finding adds a fraction. Capped at 100."""
    points = sorted((f.points for f in findings), reverse=True)
    if not points:
        return 0
    return min(100, round(points[0] + cfg.EXTRA_FINDING_WEIGHT * sum(points[1:])))


def scan(path) -> ScanResult:
    """Full pipeline: extract -> visibility checks -> intent -> risk score."""
    doc = extract(path)
    findings = run_all_checks(doc)
    for f in findings:
        f.intent, f.intent_score = analyze_intent(f.text)
        f.points = cfg.POINTS[f.intent]
        f.reason += " " + INTENT_SENTENCE[f.intent]
    hidden_ids = {i for f in findings for i in f.span_ids}
    score = score_findings(findings)
    return ScanResult(doc=doc, findings=findings, score=score, level=risk_level(score), hidden_ids=hidden_ids)
