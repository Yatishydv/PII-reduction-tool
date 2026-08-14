"""Tests for PhoneDetector."""
import pytest
from src.detectors.regex_detectors import PhoneDetector


@pytest.fixture
def detector():
    return PhoneDetector()


@pytest.mark.parametrize("text,expected_substring", [
    ("Telephone: + 91 20 4505 3237", "91 20 4505 3237"),
    ("Tel: +91 22 40094400", "+91 22 40094400"),
    ("Phone: +91-20-26234000", "+91-20-26234000"),
    ("Contact: +91 81081 14949", "+91 81081 14949"),
    ("Call +91 20 6606 4494 for support", "+91 20 6606 4494"),
    ("+91 22 30752929", "+91 22 30752929"),
])
def test_phone_detected(detector, text, expected_substring):
    entities = detector.detect(text)
    detected_texts = " ".join(e.text for e in entities)
    assert expected_substring.replace(" ", "") in detected_texts.replace(" ", ""), \
        f"Expected {expected_substring!r} in results: {[e.text for e in entities]}"


@pytest.mark.parametrize("text", [
    "FY2025 revenue was ₹7,100 million",
    "Page 200 of the prospectus",
    "CIN: U28129PN1979PLC141032",
    "Equity shares: 56,906,382",
    "₹5 each face value",
    "Fiscal year 2024-25",
    "Section 32 of the Companies Act",
])
def test_phone_not_detected(detector, text):
    entities = detector.detect(text)
    assert len(entities) == 0, f"False positive in: {text!r} → {[e.text for e in entities]}"


def test_phone_label(detector):
    entities = detector.detect("+91 22 40094400")
    assert all(e.label == "PHONE" for e in entities)
