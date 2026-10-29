"""Risk scoring and the end-to-end scan on a few generated resumes plus two shipped samples."""

from conftest import TEXT, ROOT
from hiddenink.models import Finding
from hiddenink.scoring import risk_level, scan, score_findings


def test_risk_levels():
    assert risk_level(0) == "Low" and risk_level(24) == "Low"
    assert risk_level(25) == "Medium" and risk_level(59) == "Medium"
    assert risk_level(60) == "High"


def test_score_combines_and_caps():
    assert score_findings([]) == 0
    assert score_findings([Finding("a", "", "", points=60)]) == 60
    many = [Finding("a", "", "", points=60) for _ in range(10)]
    assert score_findings(many) == 100


def test_scan_clean(build):
    result = scan(build("pdf"))
    assert result.level == "Low" and result.findings == []


def test_scan_hidden_instruction_is_high(build):
    extra = {"technique": "low_contrast", "text": TEXT, "color": (255, 255, 255)}
    result = scan(build("pdf", [extra]))
    assert result.level == "High"
    assert result.findings[0].intent == "instruction"
    assert "AI" in result.findings[0].reason
    assert result.hidden_ids  # the hidden span is marked for the UI


def test_scan_hidden_keywords_is_medium(build):
    stuffing = "Python, Java, C++, SQL, Machine Learning, AWS, Docker, Kubernetes, Agile, Scrum"
    extra = {"technique": "docx_vanish", "text": stuffing}
    assert scan(build("docx", [extra])).level == "Medium"


def test_shipped_samples():
    data = ROOT / "data"
    assert scan(data / "clean/clean_00.pdf").level == "Low"
    assert scan(data / "manipulated/manip_00.pdf").level == "High"
