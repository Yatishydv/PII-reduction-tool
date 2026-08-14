"""Tests for EmailDetector."""
import pytest
from src.detectors.regex_detectors import EmailDetector


@pytest.fixture
def detector():
    return EmailDetector()


# --- Positive cases (should detect) ---

@pytest.mark.parametrize("text,expected", [
    ("Contact: john@example.com for details", "john@example.com"),
    ("Send to john.doe@example.com now", "john.doe@example.com"),
    ("Email: rashi.patil@gmail.com", "rashi.patil@gmail.com"),
    ("admin+tag@company.co.in is valid", "admin+tag@company.co.in"),
    ("cs.connect@kshinternational.com", "cs.connect@kshinternational.com"),
    ("ksh.ipo@nuvama.com", "ksh.ipo@nuvama.com"),
    ("hitesh.ramani@citi.com", "hitesh.ramani@citi.com"),
    ("Sarthak.malvadkar@kshinterantional.com", "Sarthak.malvadkar@kshinterantional.com"),
])
def test_email_detected(detector, text, expected):
    entities = detector.detect(text)
    texts = [e.text for e in entities]
    assert expected in texts, f"Expected {expected!r} in {texts}"


# --- Negative cases (should NOT detect) ---

@pytest.mark.parametrize("text", [
    "The price is ₹7,100 million",
    "Version 3.8.13 released",
    "Page 42 of the document",
    "See section 32 for details",
    "Fiscal Year 2025",
    "INM000013004 is not an email",
    "www.kshinternational.com",        # URL without @
    "www.example.co.in",
])
def test_email_not_detected(detector, text):
    entities = detector.detect(text)
    assert len(entities) == 0, f"False positive in: {text!r} → {entities}"


# --- Label check ---

def test_email_label(detector):
    entities = detector.detect("test@example.com")
    assert all(e.label == "EMAIL" for e in entities)


# --- Confidence check ---

def test_email_confidence(detector):
    entities = detector.detect("user@domain.com")
    assert all(e.confidence >= 0.9 for e in entities)
