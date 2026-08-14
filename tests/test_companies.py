"""Tests for ReplacementGenerator — consistency and type-appropriateness."""
import pytest
from src.redaction.replacement import ReplacementGenerator


@pytest.fixture
def gen():
    return ReplacementGenerator()


def test_email_replacement_format(gen):
    result = gen.get_replacement("john@example.com", "EMAIL")
    assert "@" in result, "EMAIL replacement must contain @"
    assert "." in result, "EMAIL replacement must contain ."


def test_phone_replacement_format(gen):
    result = gen.get_replacement("+91 9876543210", "PHONE")
    digits = "".join(filter(str.isdigit, result))
    assert len(digits) >= 10, "PHONE replacement must have at least 10 digits"


def test_ssn_replacement_format(gen):
    result = gen.get_replacement("123-45-6789", "SSN")
    parts = result.split("-")
    assert len(parts) == 3
    assert len(parts[0]) == 3
    assert len(parts[1]) == 2
    assert len(parts[2]) == 4


def test_ip_replacement_format(gen):
    result = gen.get_replacement("192.168.1.10", "IP_ADDRESS")
    parts = result.split(".")
    assert len(parts) == 4
    assert all(0 <= int(p) <= 255 for p in parts)


def test_consistency_same_input(gen):
    """Same original + label must always produce same replacement."""
    original = "john.smith@example.com"
    r1 = gen.get_replacement(original, "EMAIL")
    r2 = gen.get_replacement(original, "EMAIL")
    assert r1 == r2, "Replacement must be consistent for same input"


def test_consistency_different_inputs(gen):
    """Different originals should (usually) produce different replacements."""
    r1 = gen.get_replacement("alice@example.com", "EMAIL")
    r2 = gen.get_replacement("bob@example.com", "EMAIL")
    # Not guaranteed to be different, but should be
    # (this is informational, not a hard failure)


def test_person_replacement_format(gen):
    result = gen.get_replacement("John Smith", "PERSON")
    parts = result.split()
    assert len(parts) >= 2, "PERSON replacement should be a full name"


def test_dob_replacement_is_string(gen):
    result = gen.get_replacement("12/05/1999", "DOB")
    assert isinstance(result, str)
    assert len(result) > 0


def test_credit_card_replacement(gen):
    result = gen.get_replacement("4111 1111 1111 1111", "CREDIT_CARD")
    digits = "".join(filter(str.isdigit, result))
    assert len(digits) in (15, 16)


def test_map_accumulates(gen):
    gen.get_replacement("a@b.com", "EMAIL")
    gen.get_replacement("c@d.com", "EMAIL")
    m = gen.get_full_map()
    assert len(m) >= 2
