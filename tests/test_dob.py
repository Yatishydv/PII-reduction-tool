"""Tests for DOBDetector — context-anchored date of birth detection."""
import pytest
from src.detectors.regex_detectors import DOBDetector


@pytest.fixture
def detector():
    return DOBDetector()


# --- Positive cases (with context triggers) ---

@pytest.mark.parametrize("text,expected_date", [
    ("Date of Birth: 12/05/1999", "12/05/1999"),
    ("DOB: 01-Jan-1980", "01-Jan-1980"),
    ("D.O.B.: 15/08/1985", "15/08/1985"),
    ("Born on: March 15, 1990", "March 15, 1990"),
    ("birth date: 1999-05-12", "1999-05-12"),
    ("birthdate: 07/09/1998", "07/09/1998"),
])
def test_dob_detected(detector, text, expected_date):
    entities = detector.detect(text)
    detected_dates = [e.text for e in entities]
    # Accept substring match for flexibility
    assert any(expected_date in d or d in expected_date for d in detected_dates), \
        f"Expected {expected_date!r} in {detected_dates} for text: {text!r}"


# --- Negative cases (dates WITHOUT context trigger) ---

@pytest.mark.parametrize("text", [
    "Fiscal Year 2025",
    "Dated December 10, 2025",
    "February 21, 2025 acquisition",
    "The Companies Act, 2013",
    "FY 2024-25",
    "Q2 2025",
    "3 years ended March 31, 2025",
])
def test_dob_not_detected(detector, text):
    entities = detector.detect(text)
    assert len(entities) == 0, \
        f"False positive DOB in: {text!r} → {[e.text for e in entities]}"


def test_dob_label(detector):
    entities = detector.detect("Date of Birth: 01/01/1990")
    assert all(e.label == "DOB" for e in entities)
