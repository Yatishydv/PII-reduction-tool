"""Tests for CreditCardDetector with Luhn validation."""
import pytest
from src.detectors.regex_detectors import CreditCardDetector, _luhn_check


@pytest.fixture
def detector():
    return CreditCardDetector()


# --- Luhn algorithm unit tests ---

def test_luhn_valid_visa():
    assert _luhn_check("4111111111111111") is True

def test_luhn_valid_mastercard():
    assert _luhn_check("5500000000000004") is True

def test_luhn_invalid():
    assert _luhn_check("1234567890123456") is False

def test_luhn_random_invalid():
    # A random 16-digit number that doesn't pass Luhn
    assert _luhn_check("1234567890123456") is False


# --- Positive detection cases ---

@pytest.mark.parametrize("text,expected_digits", [
    ("Card: 4111 1111 1111 1111", "4111111111111111"),
    ("4111-1111-1111-1111 is a test card", "4111111111111111"),
    ("5500-0000-0000-0004", "5500000000000004"),
])
def test_cc_detected(detector, text, expected_digits):
    entities = detector.detect(text)
    detected_digits = ["".join(filter(str.isdigit, e.text)) for e in entities]
    assert expected_digits in detected_digits, f"Expected {expected_digits!r} in {detected_digits}"


# --- False positive cases (must NOT be detected) ---

@pytest.mark.parametrize("text", [
    "₹7,100 million revenue",
    "CIN: U28129PN1979PLC141032",       # CIN number
    "Shares: 10,907,771",
    "INM000013004 is a SEBI number",
    "Section 32 of the Companies Act, 2013",
    "₹11,111.11 disbursed",
    "1234 5678 9012 3456",              # Does not pass Luhn
])
def test_cc_not_detected(detector, text):
    entities = detector.detect(text)
    assert len(entities) == 0, f"False positive in: {text!r} → {[e.text for e in entities]}"


def test_cc_label(detector):
    entities = detector.detect("4111 1111 1111 1111")
    assert all(e.label == "CREDIT_CARD" for e in entities)
