"""Tests for IPDetector."""
import pytest
from src.detectors.regex_detectors import IPDetector


@pytest.fixture
def detector():
    return IPDetector()


@pytest.mark.parametrize("text,expected", [
    ("Server at 192.168.1.10", "192.168.1.10"),
    ("IP: 10.0.0.254", "10.0.0.254"),
    ("Client IP was 203.0.113.42", "203.0.113.42"),
    ("Gateway 172.16.0.1 is configured", "172.16.0.1"),
])
def test_ip_detected(detector, text, expected):
    entities = detector.detect(text)
    assert any(e.text == expected for e in entities), \
        f"Expected {expected!r} in {[e.text for e in entities]}"


@pytest.mark.parametrize("text", [
    "Version 3.8.13 of spaCy",
    "2025.12.20",                # Date-like, not IP
    "256.0.0.1",                 # Invalid octet
    "₹7,100.5 million",
    "CIN: U28129PN1979PLC141032",
    "99999.1.1.1",               # Invalid
])
def test_ip_not_detected(detector, text):
    entities = detector.detect(text)
    valid = [e for e in entities if all(0 <= int(p) <= 255 for p in e.text.split("."))]
    assert len(valid) == 0, f"False positive in: {text!r} → {valid}"


def test_ip_label(detector):
    entities = detector.detect("10.20.30.40")
    assert all(e.label == "IP_ADDRESS" for e in entities)
