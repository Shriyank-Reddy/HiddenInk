"""Intent check: is a piece of hidden text trying to give orders to an AI?

Two signals are combined (take the max):
  1. Regex rules for classic injection phrasing.
  2. A small TF-IDF + logistic-regression classifier trained on intent_data.py.
Hidden text that is a long list of short items is labeled "keyword_stuffing".
"""
import re
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from . import config as cfg
from .intent_data import NEGATIVES, POSITIVES

_AI_WORDS = r"(ai|a\.i\.|llm|language model|model|assistant|chatbot|bot|screener|screening|ats|algorithm|system|machine)"
_RULES = [
    r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|earlier|all|other|your|the)\b.{0,30}"
    r"\b(instructions?|prompts?|rules?|guidance|applicants?|candidates?|criteria|rubric)\b",
    r"\b(system prompt|prompt injection)\b",
    rf"\b{_AI_WORDS}\b.{{0,60}}\b(rank|rate|score|recommend|select|shortlist|prioriti[sz]e|approve|hire)\b",
    r"\b(rank|rate|score|recommend|select|shortlist|approve)\b.{0,40}\b(this|the)\b.{0,15}"
    r"\b(candidate|applicant|resume|cv)\b.{0,50}\b(top|first|highest|best|strongest|perfect|10/10|above all)\b",
    r"\byou (are|must|should|will)\b.{0,40}\b(assistant|recruiter|screener|ai|rate|rank|state|approve|recommend)\b",
    r"\bdo not (mention|reveal|flag|tell|disclose)\b",
    r"\bif you are (an? )?(ai|llm|bot|language model|assistant)\b",
]
_RULE_RES = [re.compile(r, re.IGNORECASE | re.DOTALL) for r in _RULES]


def clean_text(text: str) -> str:
    """Remove zero-width characters so obfuscated words are rejoined before analysis."""
    return text.translate({ord(c): None for c in cfg.ZERO_WIDTH_CHARS})


@lru_cache(maxsize=1)
def _classifier():
    """Train once (takes milliseconds on ~230 sentences); no model file is saved."""
    texts = POSITIVES + NEGATIVES
    labels = [1] * len(POSITIVES) + [0] * len(NEGATIVES)
    model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), lowercase=True, sublinear_tf=True),
                          LogisticRegression(C=10, max_iter=1000, class_weight="balanced"))
    return model.fit(texts, labels)


def _sentences(text: str) -> list:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 3]


def rule_score(text: str) -> float:
    return cfg.RULE_SCORE if any(r.search(text) for r in _RULE_RES) else 0.0


def classifier_score(text: str) -> float:
    """Highest probability of 'instruction' over the sentences in the text."""
    sentences = _sentences(text) or [text]
    return float(max(_classifier().predict_proba(sentences)[:, 1]))


def is_keyword_stuffing(text: str) -> bool:
    items = [i.strip() for i in re.split(r"[,;|•\n]", text) if i.strip()]
    if len(items) < cfg.STUFFING_MIN_ITEMS:
        return False
    return sum(len(i.split()) <= cfg.STUFFING_MAX_WORDS_PER_ITEM for i in items) / len(items) >= 0.8


def analyze_intent(text: str) -> tuple:
    """Return (label, score): label in {'instruction', 'keyword_stuffing', 'other'}."""
    text = clean_text(text)
    score = max(rule_score(text), classifier_score(text))
    if score >= cfg.INTENT_THRESHOLD:
        return "instruction", score
    if is_keyword_stuffing(text):
        return "keyword_stuffing", 0.5
    return "other", score
