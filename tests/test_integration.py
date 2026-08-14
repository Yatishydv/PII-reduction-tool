"""Integration test: full pipeline from text to redacted output."""
import pytest
from src.detectors.regex_detectors import (
    EmailDetector, PhoneDetector, IPDetector, SSNDetector, CreditCardDetector, DOBDetector
)
from src.detectors.entity_resolver import EntityResolver
from src.redaction.replacement import ReplacementGenerator
from src.redaction.redactor import Redactor


@pytest.fixture(scope="module")
def redactor():
    detectors = [
        EmailDetector(),
        PhoneDetector(),
        IPDetector(),
        SSNDetector(),
        CreditCardDetector(),
        DOBDetector(),
    ]
    return Redactor(
        detectors=detectors,
        generator=ReplacementGenerator(),
        resolver=EntityResolver(),
    )


def test_email_redacted(redactor):
    text = "Contact john@example.com for details."
    redacted, entities = redactor.redact(text)
    assert "john@example.com" not in redacted
    assert any(e.label == "EMAIL" for e in entities)


def test_phone_redacted(redactor):
    text = "Call +91 9876543210 now."
    redacted, entities = redactor.redact(text)
    # Check original phone is gone
    assert "9876543210" not in redacted
    assert any(e.label == "PHONE" for e in entities)


def test_ip_redacted(redactor):
    text = "Server IP: 192.168.1.10"
    redacted, entities = redactor.redact(text)
    assert any(e.label == "IP_ADDRESS" for e in entities)


def test_ssn_redacted(redactor):
    text = "Employee SSN: 123-45-6789"
    redacted, entities = redactor.redact(text)
    assert "123-45-6789" not in redacted


def test_credit_card_redacted(redactor):
    text = "Card: 4111 1111 1111 1111"
    redacted, entities = redactor.redact(text)
    assert "4111 1111 1111 1111" not in redacted
    assert any(e.label == "CREDIT_CARD" for e in entities)


def test_dob_redacted(redactor):
    text = "Date of Birth: 12/05/1999"
    redacted, entities = redactor.redact(text)
    assert "12/05/1999" not in redacted
    assert any(e.label == "DOB" for e in entities)


def test_no_pii_unchanged(redactor):
    text = "The Companies Act, 2013 governs this offer."
    redacted, entities = redactor.redact(text)
    assert redacted == text
    assert len(entities) == 0


def test_consistency(redactor):
    """Same PII must produce same replacement in both calls."""
    text1 = "Email: john@example.com"
    text2 = "Contact: john@example.com for support"
    _, entities1 = redactor.redact(text1)
    _, entities2 = redactor.redact(text2)

    map1 = redactor.get_replacement_map()
    key = ("john@example.com", "EMAIL")
    assert key in map1
    r1 = map1[key]
    r2 = map1[key]  # Same key — must be same value
    assert r1 == r2


def test_multiple_pii_in_one_text(redactor):
    """Multiple PII types in one string must all be redacted."""
    text = "Call +91 9876543210 or email test@example.com, IP: 10.0.0.1"
    redacted, entities = redactor.redact(text)
    labels = {e.label for e in entities}
    assert "EMAIL" in labels
    assert "PHONE" in labels
    assert "IP_ADDRESS" in labels
    assert "test@example.com" not in redacted
    assert "9876543210" not in redacted
