"""Plain data containers shared by all modules."""
from dataclasses import dataclass, field


@dataclass
class Span:
    """One piece of text with the same style (a PDF span or a DOCX run)."""
    index: int
    text: str
    size: float                 # font size in points
    color: tuple                # (r, g, b), each 0-255
    bold: bool = False
    bbox: tuple | None = None   # (x0, y0, x1, y1) in PDF points; None for DOCX
    page: int = 0
    hidden_prop: bool = False   # DOCX "vanish" property
    highlight: tuple | None = None  # DOCX highlight color behind the text


@dataclass
class FilledRect:
    """A filled rectangle drawn on a PDF page (a possible cover-up)."""
    page: int
    bbox: tuple
    fill: tuple


@dataclass
class ExtractedDoc:
    path: str
    fmt: str                            # "pdf" or "docx"
    spans: list = field(default_factory=list)
    rects: list = field(default_factory=list)
    page_sizes: list = field(default_factory=list)  # [(width, height), ...]
    metadata: dict = field(default_factory=dict)


@dataclass
class Finding:
    technique: str          # e.g. "low_contrast"
    reason: str             # plain-English explanation
    text: str               # the hidden text itself
    span_ids: list = field(default_factory=list)
    intent: str = "other"   # "instruction" | "keyword_stuffing" | "other"
    intent_score: float = 0.0
    points: int = 0


@dataclass
class ScanResult:
    doc: ExtractedDoc
    findings: list
    score: int
    level: str              # "Low" | "Medium" | "High"
    hidden_ids: set
