"""Read a PDF and return every text span with its style and position (PyMuPDF)."""
import pymupdf

from .models import ExtractedDoc, FilledRect, Span


def _to_rgb(color) -> tuple:
    """PyMuPDF gives colors as 0-1 floats (gray/RGB tuples); convert to 0-255 RGB."""
    if color is None:
        return (0, 0, 0)
    if len(color) == 1:
        color = color * 3
    return tuple(round(c * 255) for c in color[:3])


def _int_to_rgb(value: int) -> tuple:
    """Span colors come as one integer 0xRRGGBB."""
    return ((value >> 16) & 255, (value >> 8) & 255, value & 255)


def extract_pdf(path) -> ExtractedDoc:
    doc = ExtractedDoc(path=str(path), fmt="pdf")
    pdf = pymupdf.open(path)
    meta = pdf.metadata or {}
    doc.metadata = {k: meta.get(k) or "" for k in ("title", "author", "subject", "keywords")}

    for page_no, page in enumerate(pdf):
        doc.page_sizes.append((page.rect.width, page.rect.height))

        # Filled rectangles: they might be covering text (or just be a colored header bar).
        for shape in page.get_drawings():
            if shape.get("fill") is not None and (shape.get("fill_opacity") or 1) > 0:
                r = shape["rect"]
                doc.rects.append(FilledRect(page_no, (r.x0, r.y0, r.x1, r.y1), _to_rgb(shape["fill"])))

        # By default MuPDF drops text outside the page. We WANT off-page text, so pass an infinite clip.
        data = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE, clip=pymupdf.INFINITE_RECT())
        for block in data["blocks"]:
            for line in block.get("lines", []):
                for s in line["spans"]:
                    if not s["text"].strip():
                        continue
                    doc.spans.append(Span(
                        index=len(doc.spans), text=s["text"], size=round(s["size"], 2),
                        color=_int_to_rgb(s["color"]), bold=bool(s["flags"] & 16),
                        bbox=tuple(s["bbox"]), page=page_no))
    return doc
