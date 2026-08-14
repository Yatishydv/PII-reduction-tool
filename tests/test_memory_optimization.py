import sys
import gc
import pytest
from pathlib import Path

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.detectors.ner_detector import NERDetector
from src.detectors.address_detector import AddressDetector
from src.redaction.replacement import ReplacementGenerator
from src.docx_processor import DocxProcessor


def test_ner_detector_fast_precheck():
    detector = NERDetector()
    # Numeric string without uppercase characters should return [] instantly without calling spaCy
    res = detector.detect("100.00")
    assert res == []

    res_lower = detector.detect("sample lower text without names")
    assert res_lower == []

    # Valid name with uppercase characters should be detected
    res_valid = detector.detect("Arjun Mehta visited the office")
    assert len(res_valid) > 0
    assert any(e.text == "Arjun Mehta" for e in res_valid)


def test_address_detector_fast_precheck():
    detector = AddressDetector()
    # String without address anchor keywords should return [] instantly
    res = detector.detect("The financial metrics for FY2024 were 12.5 percent.")
    assert res == []


def test_replacement_generator_clear():
    gen = ReplacementGenerator()
    gen.get_replacement("test@example.com", "EMAIL")
    assert len(gen.get_full_map()) == 1

    gen.clear()
    assert len(gen.get_full_map()) == 0


def test_docx_processor_lightweight_validate(tmp_path):
    out_file = tmp_path / "test.docx"
    
    # Non-existent file
    val_missing = DocxProcessor.validate(tmp_path / "non_existent.docx")
    assert not val_missing["valid"]

    # Non-docx file
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("hello")
    val_txt = DocxProcessor.validate(txt_file)
    assert not val_txt["valid"]
