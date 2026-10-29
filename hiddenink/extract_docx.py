"""Read a DOCX and return every run with its font color, size, hidden flag and highlight."""
from docx import Document
from docx.enum.text import WD_COLOR_INDEX

from .models import ExtractedDoc, Span

DEFAULT_SIZE = 11.0  # Word's usual default when no size is set anywhere

HIGHLIGHT_RGB = {
    WD_COLOR_INDEX.YELLOW: (255, 255, 0), WD_COLOR_INDEX.WHITE: (255, 255, 255),
    WD_COLOR_INDEX.BLACK: (0, 0, 0), WD_COLOR_INDEX.BLUE: (0, 0, 255),
    WD_COLOR_INDEX.RED: (255, 0, 0), WD_COLOR_INDEX.GREEN: (0, 255, 0),
}


def _paragraphs(document):
    """Body paragraphs, table-cell paragraphs, then headers/footers."""
    yield from document.paragraphs
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs
    for section in document.sections:
        yield from section.header.paragraphs
        yield from section.footer.paragraphs


def _run_size(run, paragraph) -> float:
    if run.font.size:
        return run.font.size.pt
    if paragraph.style is not None and paragraph.style.font.size:
        return paragraph.style.font.size.pt
    return DEFAULT_SIZE


def extract_docx(path) -> ExtractedDoc:
    doc = ExtractedDoc(path=str(path), fmt="docx")
    document = Document(path)
    cp = document.core_properties
    doc.metadata = {"title": cp.title or "", "author": cp.author or "",
                    "subject": cp.subject or "", "keywords": cp.keywords or "",
                    "comments": cp.comments or ""}

    for paragraph in _paragraphs(document):
        for run in paragraph.runs:
            if not run.text.strip():
                continue
            rgb = run.font.color.rgb if run.font.color and run.font.color.type is not None else None
            doc.spans.append(Span(
                index=len(doc.spans), text=run.text, size=_run_size(run, paragraph),
                color=tuple(rgb) if rgb is not None else (0, 0, 0),   # theme/auto color -> black
                bold=bool(run.font.bold), hidden_prop=bool(run.font.hidden),
                highlight=HIGHLIGHT_RGB.get(run.font.highlight_color)))
    return doc


def extract(path) -> ExtractedDoc:
    """Pick the right extractor from the file extension."""
    from .extract_pdf import extract_pdf
    suffix = str(path).lower().rsplit(".", 1)[-1]
    if suffix == "pdf":
        return extract_pdf(path)
    if suffix == "docx":
        return extract_docx(path)
    raise ValueError(f"Unsupported file type: .{suffix} (use PDF or DOCX)")
