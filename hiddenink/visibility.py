"""Visibility checks: which text could a human NOT see, but an AI would read?

Each check takes an ExtractedDoc and returns a list of Findings (one per technique,
grouping all spans caught by that check). Intent/severity are filled in later by scoring.py.
"""
from . import config as cfg
from .intent import analyze_intent
from .models import Finding

WHITE = (255, 255, 255)


def _luminance(rgb) -> float:
    """Relative luminance from the WCAG accessibility standard (0 = black, 1 = white)."""
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(c1, c2) -> float:
    """1.0 = identical colors, 21.0 = black on white. Below ~1.5 text is basically invisible."""
    l1, l2 = sorted((_luminance(c1), _luminance(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _intersection(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def _fraction_inside(span_box, other_box) -> float:
    area = _area(span_box)
    if area == 0:  # zero-height text (extremely tiny): fall back to its center point
        cx, cy = (span_box[0] + span_box[2]) / 2, (span_box[1] + span_box[3]) / 2
        return 1.0 if other_box[0] <= cx <= other_box[2] and other_box[1] <= cy <= other_box[3] else 0.0
    return _area(_intersection(span_box, other_box)) / area


def _enclosing_rect(span, doc):
    """The filled rectangle (if any) that mostly contains this span."""
    if span.bbox is None:
        return None
    for rect in doc.rects:
        if rect.page == span.page and _fraction_inside(span.bbox, rect.bbox) >= cfg.COVERED_INSIDE_FRAC:
            return rect
    return None


def _finding(technique, spans, reason) -> Finding | None:
    if not spans:
        return None
    return Finding(technique=technique, reason=reason, span_ids=[s.index for s in spans],
                   text=" ".join(s.text.strip() for s in spans))


# --- The checks --------------------------------------------------------------

def check_low_contrast(doc):
    """Technique 1: text color (almost) equals the background color, e.g. white on white."""
    hits, worst = [], 99.0
    for s in doc.spans:
        if _enclosing_rect(s, doc) is not None:
            continue  # text on a colored shape is handled by check_covered_by_shape
        bg = s.highlight or WHITE
        ratio = contrast_ratio(s.color, bg)
        if ratio < cfg.LOW_CONTRAST_RATIO:
            hits.append(s)
            worst = min(worst, ratio)
    return _finding("low_contrast", hits,
                    f"{len(hits)} text span(s) are nearly the same color as the page background "
                    f"(contrast {worst:.2f}:1, limit {cfg.LOW_CONTRAST_RATIO}:1). A person cannot read "
                    "them, but an AI reads them like normal text.")


def check_tiny_font(doc):
    """Technique 2: font so small that no human can read it."""
    hits = [s for s in doc.spans if s.size < cfg.TINY_FONT_PT]
    smallest = min((s.size for s in hits), default=0)
    return _finding("tiny_font", hits,
                    f"{len(hits)} text span(s) use a font of {smallest:g} pt (limit {cfg.TINY_FONT_PT:g} pt). "
                    "That is far too small to read, yet the text is still extracted by AI tools.")


def check_off_page(doc):
    """Technique 3: text placed outside the visible page area (PDF only)."""
    hits = []
    for s in doc.spans:
        if s.bbox is None:
            continue
        w, h = doc.page_sizes[s.page]
        visible = _fraction_inside(s.bbox, (0, 0, w, h))
        if visible < cfg.OFF_PAGE_VISIBLE_FRAC:
            hits.append(s)
    return _finding("off_page", hits,
                    f"{len(hits)} text span(s) sit outside the printed page area, so a reader never sees "
                    "them, but they are still stored in the file and extracted.")


def check_covered_by_shape(doc):
    """Technique 4: text sits inside a filled rectangle of (nearly) the same color (PDF only)."""
    hits = []
    for s in doc.spans:
        rect = _enclosing_rect(s, doc)
        if rect is not None and contrast_ratio(s.color, rect.fill) < cfg.LOW_CONTRAST_RATIO:
            hits.append(s)
    return _finding("covered_by_shape", hits,
                    f"{len(hits)} text span(s) are drawn inside a filled box of the same color, "
                    "so the text disappears into the shape.")


def check_docx_vanish(doc):
    """Technique 5: DOCX 'hidden text' font property (Word does not display or print it)."""
    hits = [s for s in doc.spans if s.hidden_prop]
    return _finding("docx_vanish", hits,
                    f"{len(hits)} text run(s) use Word's 'Hidden' font property: Word does not show them, "
                    "but text extraction tools still return them.")


def check_zero_width(doc):
    """Technique 7: invisible Unicode characters (used to disguise words from simple filters)."""
    hits = [s for s in doc.spans
            if sum(s.text.count(ch) for ch in cfg.ZERO_WIDTH_CHARS) >= cfg.ZERO_WIDTH_MIN]
    return _finding("zero_width", hits,
                    f"{len(hits)} text span(s) contain {cfg.ZERO_WIDTH_MIN}+ invisible zero-width characters, "
                    "a trick to hide or disguise words from keyword filters.")


def check_metadata(doc):
    """Technique 6: document properties (title/author/subject/keywords/comments) that are
    unusually long OR read like an instruction to an AI. One Finding per suspicious field.
    """
    findings = []
    for field in cfg.METADATA_FIELDS:
        value = (doc.metadata.get(field) or "").strip()
        if len(value) > cfg.METADATA_MAX_LEN or analyze_intent(value)[0] == "instruction":
            findings.append(Finding(
                technique="metadata", text=value,
                reason=f"The document's '{field}' property holds {len(value)} characters that look like "
                       "more than a normal label. People rarely see metadata, but some AI tools read it."))
    return findings


SPAN_CHECKS = [check_low_contrast, check_tiny_font, check_off_page, check_covered_by_shape,
               check_docx_vanish, check_zero_width]


def run_all_checks(doc) -> list:
    findings = [f for check in SPAN_CHECKS if (f := check(doc))]
    findings += check_metadata(doc)
    return findings
