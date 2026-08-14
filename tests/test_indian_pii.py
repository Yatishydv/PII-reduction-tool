"""Tests for Indian PII detectors: PAN, Aadhaar, Bank Account, IFSC, DIN, GSTIN, CIN."""
import pytest
from src.detectors.regex_detectors import (
    PANDetector, AadhaarDetector, BankAccountDetector,
    IFSCDetector, DINDetector, GSTINDetector, CINDetector,
)


def test_pan_detector():
    detector = PANDetector()
    text = "Customer PAN is ABCPS1234D for verification."
    entities = detector.detect(text)
    assert len(entities) == 1
    assert entities[0].text == "ABCPS1234D"
    assert entities[0].label == "PAN"


def test_aadhaar_detector():
    detector = AadhaarDetector()
    text = "Aadhaar No.: 1234 5678 9012 for citizen ID."
    entities = detector.detect(text)
    assert len(entities) == 1
    assert entities[0].text == "1234 5678 9012"
    assert entities[0].label == "AADHAAR"


def test_bank_account_detector():
    detector = BankAccountDetector()
    text = "Bank Account No.: 5012345678901234 registered."
    entities = detector.detect(text)
    assert len(entities) == 1
    assert entities[0].text == "5012345678901234"
    assert entities[0].label == "BANK_ACCOUNT"


def test_ifsc_detector():
    detector = IFSCDetector()
    text = "IFSC Code: HDFC0001234 for transfer."
    entities = detector.detect(text)
    assert len(entities) == 1
    assert entities[0].text == "HDFC0001234"
    assert entities[0].label == "IFSC_CODE"


def test_din_detector():
    detector = DINDetector()
    text = "Director Identification Number: 01234567"
    entities = detector.detect(text)
    assert len(entities) == 1
    assert entities[0].text == "01234567"
    assert entities[0].label == "DIN"


def test_cin_detector():
    detector = CINDetector()
    text = "CIN: U28129PN1979PLC141032"
    entities = detector.detect(text)
    assert len(entities) == 1
    assert entities[0].text == "U28129PN1979PLC141032"
    assert entities[0].label == "CIN"
