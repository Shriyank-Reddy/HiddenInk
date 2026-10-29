"""Helpers that build fictional resumes as PDF (reportlab) and DOCX (python-docx).

Everything here is synthetic: invented names, *.example emails, fictional schools/employers.
A resume is described by a `person` dict, a `style` dict, and a list of `extras`
(the hidden injections). The writers draw the visible resume, then the extras.
"""
import random

from docx import Document
from docx.shared import Pt, RGBColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

FIRST = ["Alder", "Briar", "Cedric", "Dalia", "Emrys", "Fenna", "Gideon", "Hollis", "Ivo", "Junia",
         "Kestrel", "Linnea", "Marlo", "Nova", "Orrin", "Perrin", "Quill", "Rowan", "Sable", "Tamsin"]
LAST = ["Applewick", "Brightmoor", "Cobblestone", "Dunmere", "Everhart", "Fairweather", "Glimmerton",
        "Hollowell", "Ironwood", "Juniper", "Kettleby", "Lowbridge", "Mistvale", "Nettlefold"]
SCHOOLS = ["Northfield Valley University", "Lakemont Institute of Technology", "Westbrook State College",
           "Ashgrove Polytechnic", "Pinecrest University"]
COMPANIES = ["Brightwave Labs", "Quillstone Software", "Harborlight Analytics", "Mapleton Systems",
             "Cedarpoint Digital", "Starling Works"]
ROLES = ["Software Engineering Intern", "Data Analyst", "Junior Developer", "IT Support Specialist",
         "Research Assistant", "QA Engineer"]
DEGREES = ["B.S. in Computer Science", "B.S. in Information Systems", "B.A. in Mathematics",
           "B.S. in Cybersecurity"]
SKILLS = ["Python", "Java", "SQL", "JavaScript", "Git", "Linux", "Docker", "React", "Flask", "C++",
          "Pandas", "REST APIs", "Unit testing", "Networking basics", "Excel"]
BULLETS = [
    "Built an internal dashboard that cut weekly reporting time by 30%.",
    "Wrote automated tests that caught regressions before each release.",
    "Cleaned and analyzed survey data for a team of five researchers.",
    "Migrated a legacy script collection to a documented Python package.",
    "Helped resolve more than 200 support tickets with a 95% satisfaction rating.",
    "Presented project results to a panel of faculty and industry mentors.",
    "Reviewed pull requests and wrote documentation for new teammates.",
    "Designed a small REST service used by two student organizations.",
]
PAGE_W, PAGE_H = letter
BAR_H = 100


def make_person(rng: random.Random) -> dict:
    first, last = rng.choice(FIRST), rng.choice(LAST)
    jobs = []
    for _ in range(2):
        jobs.append({"title": rng.choice(ROLES), "company": rng.choice(COMPANIES),
                     "dates": f"{rng.randint(2021, 2023)} - {rng.randint(2023, 2025)}",
                     "bullets": rng.sample(BULLETS, 3)})
    return {
        "name": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower()}@mail.example",
        "phone": f"555-01{rng.randint(10, 99)}",
        "summary": "Motivated computer science student with hands-on project experience and "
                   "a strong interest in building reliable, well-tested software.",
        "jobs": jobs,
        "education": f"{rng.choice(DEGREES)}, {rng.choice(SCHOOLS)}, expected {rng.randint(2025, 2027)}",
        "skills": ", ".join(rng.sample(SKILLS, 8)),
    }


def default_style(**overrides) -> dict:
    style = {"font": "Helvetica", "heading_color": (0, 0, 0), "date_color": (0, 0, 0),
             "footnote": None,          # e.g. {"text": "...", "size": 7, "color": (120, 120, 120)}
             "bar": None,               # PDF only: {"fill": (r,g,b), "text_color": (r,g,b)}
             "align": "left"}           # "left" or "right" header alignment (PDF)
    style.update(overrides)
    return style


def _lines(person: dict, style: dict) -> list:
    """The visible resume as a flat list of lines (text, size, bold, color)."""
    hc, dc = style["heading_color"], style["date_color"]
    out = [{"text": person["name"], "size": 20, "bold": True, "color": (0, 0, 0), "header": True},
           {"text": f"{person['email']}  |  {person['phone']}", "size": 10, "color": (0, 0, 0), "header": True},
           {"text": "SUMMARY", "size": 12, "bold": True, "color": hc, "gap": 8},
           {"text": person["summary"], "size": 10}]
    out.append({"text": "EXPERIENCE", "size": 12, "bold": True, "color": hc, "gap": 8})
    for job in person["jobs"]:
        out.append({"text": f"{job['title']}, {job['company']}", "size": 10.5, "bold": True})
        out.append({"text": job["dates"], "size": 9, "color": dc})
        out += [{"text": "- " + b, "size": 10} for b in job["bullets"]]
    out.append({"text": "EDUCATION", "size": 12, "bold": True, "color": hc, "gap": 8})
    out.append({"text": person["education"], "size": 10})
    out.append({"text": "SKILLS", "size": 12, "bold": True, "color": hc, "gap": 8})
    out.append({"text": person["skills"], "size": 10})
    if style["footnote"]:
        fn = style["footnote"]
        out.append({"text": fn["text"], "size": fn["size"], "color": fn["color"], "gap": 10})
    return out


def _wrap(text, font, size, width):
    words, line, lines = text.split(" "), "", []
    for w in words:
        trial = (line + " " + w).strip()
        if stringWidth(trial, font, size) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = w
    lines.append(line)
    return lines


def _rgb(c):
    return tuple(v / 255 for v in c)


def make_pdf(path, person, style, extras=(), meta=None):
    """Write a one-page PDF. extras = hidden injections drawn after the visible text."""
    c = canvas.Canvas(str(path), pagesize=letter)
    meta = meta or {}
    c.setTitle(meta.get("title", f"{person['name']} - Resume"))
    c.setAuthor(meta.get("author", person["name"]))
    c.setSubject(meta.get("subject", "Resume"))
    c.setKeywords(meta.get("keywords", "resume"))
    font = style["font"]
    bold_font = {"Helvetica": "Helvetica-Bold", "Times-Roman": "Times-Bold"}[font]
    margin, y = 54, PAGE_H - 54
    if style["bar"]:
        c.setFillColorRGB(*_rgb(style["bar"]["fill"]))
        c.rect(0, PAGE_H - BAR_H, PAGE_W, BAR_H, stroke=0, fill=1)
    for ln in _lines(person, style):
        size = ln["size"]
        f = bold_font if ln.get("bold") else font
        color = ln.get("color", (0, 0, 0))
        if ln.get("header") and style["bar"]:
            color = style["bar"]["text_color"]
        y -= ln.get("gap", 0)
        for piece in _wrap(ln["text"], f, size, PAGE_W - 2 * margin):
            y -= size * 1.3
            c.setFillColorRGB(*_rgb(color))
            c.setFont(f, size)
            x = margin
            if ln.get("header") and style["align"] == "right":
                x = PAGE_W - margin - stringWidth(piece, f, size)
            c.drawString(x, y, piece)
        if ln.get("header") and style["bar"] and ln["size"] == 10:
            y = min(y, PAGE_H - BAR_H - 6)   # body starts below the header bar
    y -= 30
    for ex in extras:
        y = _draw_extra_pdf(c, ex, y, font)
    c.save()


def _draw_extra_pdf(c, ex, y, font):
    """Draw one hidden injection. Returns the new y cursor."""
    tech, size = ex["technique"], ex.get("size", 9)
    color = ex.get("color", (0, 0, 0))
    if tech == "covered_by_shape":                     # text and its covering rectangle share a color
        n = len(_wrap(ex["text"], font, size, PAGE_W - 120))
        h = n * size * 1.3 + 8
        c.setFillColorRGB(*_rgb(color))
        c.rect(54, y - h + size, PAGE_W - 108, h, stroke=0, fill=1)
        pos = (60, y)
    elif tech == "off_page":
        pos = ex["pos"]                                # absolute position outside the page
    else:                                              # low_contrast / tiny_font
        pos = (54, y)
    c.setFillColorRGB(*_rgb(color))
    c.setFont(font, size)
    yy = pos[1]
    for piece in _wrap(ex["text"], font, size, ex.get("wrap", PAGE_W - 120)):
        c.drawString(pos[0], yy, piece)
        yy -= size * 1.3
    return y - (len(_wrap(ex["text"], font, size, PAGE_W - 120)) * size * 1.3 + 20) \
        if tech != "off_page" else y


def make_docx(path, person, style, extras=(), meta=None):
    """Write a DOCX. extras may be low_contrast / tiny_font / docx_vanish runs."""
    doc = Document()
    meta = meta or {}
    cp = doc.core_properties
    cp.title = meta.get("title", f"{person['name']} - Resume")
    cp.author = meta.get("author", person["name"])
    cp.subject = meta.get("subject", "Resume")
    cp.keywords = meta.get("keywords", "resume")
    cp.comments = meta.get("comments", "")
    for ln in _lines(person, style):
        run = doc.add_paragraph().add_run(ln["text"])
        run.font.size = Pt(ln["size"])
        run.font.bold = bool(ln.get("bold"))
        run.font.color.rgb = RGBColor(*ln.get("color", (0, 0, 0)))
    for ex in extras:
        run = doc.add_paragraph().add_run(ex["text"])
        run.font.size = Pt(ex.get("size", 9))
        run.font.color.rgb = RGBColor(*ex.get("color", (0, 0, 0)))
        if ex["technique"] == "docx_vanish":
            run.font.hidden = True
    doc.save(str(path))
