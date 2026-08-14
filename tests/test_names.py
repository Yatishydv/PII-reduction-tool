"""Tests for NERDetector — person and organization detection."""
import pytest
try:
    from src.detectors.ner_detector import NERDetector
    _NER_AVAILABLE = True
except (ImportError, RuntimeError):
    _NER_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _NER_AVAILABLE, reason="spaCy model not available"
)


@pytest.fixture(scope="module")
def detector():
    return NERDetector()


# --- Person detection ---

@pytest.mark.parametrize("text", [
    "Contact Person: John Doe is the compliance officer.",
    "Mr. Rajesh Sharma, Managing Director, signed the document.",
    "Ms. Priya Patel, Director, confirmed the details.",
])
def test_person_detected(detector, text):
    entities = detector.detect(text)
    person_ents = [e for e in entities if e.label == "PERSON"]
    assert len(person_ents) >= 1, f"Expected PERSON in: {text!r} — got {entities}"


# --- Organization detection ---

@pytest.mark.parametrize("text", [
    "Kirtane & Pandit LLP are the statutory auditors.",
    "Nuvama Wealth Management Limited arranged the IPO.",
    "The auditors are Global Finance LLP, Chartered Accountants.",
])
def test_org_detected(detector, text):
    entities = detector.detect(text)
    org_ents = [e for e in entities if e.label == "ORG"]
    # Note: spaCy sm may miss some ORG names in short, isolated contexts.
    # Full document context improves detection significantly.
    assert len(org_ents) >= 1, f"Expected ORG in: {text!r} — got {entities}"


# --- Person should NOT be detected when text is clearly an org ---

def test_org_not_misclassified_as_person(detector):
    text = "ICICI Securities Limited manages the book-building process."
    entities = detector.detect(text)
    person_ents = [e for e in entities if e.label == "PERSON" and "ICICI" in e.text]
    assert len(person_ents) == 0, f"ICICI should not be a PERSON: {entities}"


# --- Label check ---

def test_ner_labels(detector):
    entities = detector.detect("John Smith is a Director at Global Finance Limited.")
    for e in entities:
        assert e.label in ("PERSON", "ORG"), f"Unexpected label: {e.label}"
