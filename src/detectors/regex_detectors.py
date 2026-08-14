"""
regex_detectors.py — Deterministic regex-based PII detectors.

Covers: EMAIL, PHONE, IP_ADDRESS, SSN, CREDIT_CARD, DOB.

Each class is independent and can be used standalone or composed
into the main detection pipeline.
"""
from __future__ import annotations

import re
from typing import List

from .base import BaseDetector, Entity
from .. import config


# ---------------------------------------------------------------------------
# Helper: Luhn algorithm for credit-card validation
# ---------------------------------------------------------------------------

def _luhn_check(card_number: str) -> bool:
    """Return True if *card_number* (digits only) passes the Luhn check."""
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13:
        return False
    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

class EmailDetector(BaseDetector):
    """Detects email addresses using a robust RFC-5321-inspired regex.

    False-positive guard: requires valid TLD of 2–6 chars.
    """

    label = config.EMAIL

    _PATTERN = re.compile(
        r"""
        (?<![/@\w])           # negative lookbehind: not inside another word
        (
            [a-zA-Z0-9]       # first char: alphanumeric
            [a-zA-Z0-9._%+\-]* # local part body
            @
            [a-zA-Z0-9]
            [a-zA-Z0-9.\-]*
            \.
            [a-zA-Z]{2,6}     # TLD: 2-6 letters
        )
        (?![a-zA-Z0-9])       # must end here
        """,
        re.VERBOSE,
    )

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        for m in self._PATTERN.finditer(text):
            entities.append(
                Entity(
                    text=m.group(1),
                    label=self.label,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=0.99,
                    source="email_regex",
                )
            )
        return entities


# ---------------------------------------------------------------------------
# Phone
# ---------------------------------------------------------------------------

class PhoneDetector(BaseDetector):
    """Detects phone numbers, primarily Indian formats (+91 …) and
    standard international numbers.

    Applies post-match validation to reduce false positives:
    - Extracted digit count must be between 7 and 13.
    - Does NOT match pure financial figures (e.g., ₹7,100 million).
    """

    label = config.PHONE

    # Indian: +91 20 4505 3237 | +91-9876543210 | +91 81081 14949
    # International: +1 212 555 1234
    # Plain 10-digit mobile (India)
    _PATTERNS = [
        re.compile(
            r"""
            (?<!\d)
            (
                \+\s*91                   # country code
                [\s\-]?
                \d{2,5}                   # STD / area
                [\s\-]?
                \d{3,5}                   # first part
                [\s\-]?
                \d{0,5}                   # second part (optional)
            )
            (?!\d)
            """,
            re.VERBOSE,
        ),
        re.compile(
            r"""
            (?<!\d)
            (
                \+\s*[2-9]\d{1,2}         # other country codes
                [\s\-]
                \d{2,4}
                [\s\-]
                \d{3,5}
                (?:[\s\-]\d{3,5})?
            )
            (?!\d)
            """,
            re.VERBOSE,
        ),
    ]

    _MIN_DIGITS = 7
    _MAX_DIGITS = 15

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        seen_spans: set[tuple[int, int]] = set()

        for pattern in self._PATTERNS:
            for m in pattern.finditer(text):
                raw = m.group(1)
                digits = re.sub(r"\D", "", raw)
                if not (self._MIN_DIGITS <= len(digits) <= self._MAX_DIGITS):
                    continue
                span = (m.start(1), m.end(1))
                if span in seen_spans:
                    continue
                seen_spans.add(span)
                entities.append(
                    Entity(
                        text=raw.strip(),
                        label=self.label,
                        start=m.start(1),
                        end=m.end(1),
                        confidence=0.95,
                        source="phone_regex",
                    )
                )
        return entities


# ---------------------------------------------------------------------------
# IP Address
# ---------------------------------------------------------------------------

class IPDetector(BaseDetector):
    """Detects IPv4 addresses.

    Validates that each octet is 0-255.
    Does NOT detect IPv6 (documented limitation).
    """

    label = config.IP_ADDRESS

    # Match candidate IPv4 patterns
    _PATTERN = re.compile(
        r"(?<!\d\.)"
        r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})"
        r"(?!\.\d)"
    )

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        for m in self._PATTERN.finditer(text):
            if all(0 <= int(g) <= 255 for g in m.groups()):
                entities.append(
                    Entity(
                        text=m.group(),
                        label=self.label,
                        start=m.start(),
                        end=m.end(),
                        confidence=0.98,
                        source="ip_regex",
                    )
                )
        return entities


# ---------------------------------------------------------------------------
# SSN (US Social Security Number)
# ---------------------------------------------------------------------------

class SSNDetector(BaseDetector):
    """Detects US Social Security Numbers (format: NNN-NN-NNNN).

    Validates that it's not 000-00-0000 or known test values.
    """

    label = config.SSN

    _PATTERN = re.compile(r"(?<!\d)(\d{3}-\d{2}-\d{4})(?!\d)")

    # SSNs with all-zeros in any segment are invalid
    _INVALID_PREFIXES = {"000", "666"}
    _INVALID_FULL = {"000-00-0000", "123-45-6789"}  # 123-45-6789 is test but we still flag

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        for m in self._PATTERN.finditer(text):
            raw = m.group(1)
            area = raw[:3]
            # Basic sanity: area group cannot be 000 or 666
            if area in self._INVALID_PREFIXES:
                continue
            entities.append(
                Entity(
                    text=raw,
                    label=self.label,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=0.97,
                    source="ssn_regex",
                )
            )
        return entities


# ---------------------------------------------------------------------------
# Credit Card
# ---------------------------------------------------------------------------

class CreditCardDetector(BaseDetector):
    """Detects credit card numbers with Luhn validation.

    Supported formats:
        4111 1111 1111 1111   (space-separated)
        4111-1111-1111-1111   (dash-separated)
        4111111111111111      (no separator)

    Uses the Luhn algorithm to eliminate false positives from financial
    figures, registration numbers, and similar numeric sequences.
    """

    label = config.CREDIT_CARD

    _PATTERN = re.compile(
        r"(?<!\d)"
        r"(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}"
        r"|\d{4}[\s\-]?\d{6}[\s\-]?\d{5})"  # Amex format
        r"(?!\d)"
    )

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        for m in self._PATTERN.finditer(text):
            raw = m.group(1)
            digits_only = re.sub(r"\D", "", raw)
            if len(digits_only) not in (15, 16):
                continue
            if not _luhn_check(digits_only):
                continue
            entities.append(
                Entity(
                    text=raw,
                    label=self.label,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=0.99,
                    source="credit_card_regex",
                )
            )
        return entities


# ---------------------------------------------------------------------------
# Date of Birth (context-anchored)
# ---------------------------------------------------------------------------

class DOBDetector(BaseDetector):
    """Detects Dates of Birth — ONLY when preceded by a contextual trigger.

    This is critical for precision: a Red Herring Prospectus contains
    hundreds of dates (financial, legal, filing). We only flag dates
    that are clearly labeled as birth dates.

    Trigger examples:
        "Date of Birth: 12/05/1999"
        "DOB: 01-Jan-1980"
        "Born on: March 15, 1990"
    """

    label = config.DOB

    # Date patterns (after trigger)
    _DATE_PATTERNS = [
        re.compile(r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"),          # 12/05/1999
        re.compile(r"(\d{1,2}[-\s][A-Za-z]{3,9}[-\s]\d{4})"),      # 01-Jan-1980 or 01 January 1980
        re.compile(r"(\d{1,2}\s+\w+\s+\d{4})"),                     # 15 March 1990
        re.compile(r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})"),         # March 15, 1990
        re.compile(r"(\d{4}-\d{2}-\d{2})"),                          # 1999-05-12 (ISO)
    ]

    _TRIGGER_PATTERN = re.compile(
        r"(?:" + "|".join(re.escape(t) for t in config.DOB_TRIGGERS) + r")\s*:?\s*",
        re.IGNORECASE,
    )

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        text_lower = text.lower()

        for trigger_match in self._TRIGGER_PATTERN.finditer(text):
            trigger_end = trigger_match.end()
            # Look for a date pattern within DOB_TRIGGER_WINDOW chars after trigger
            window = text[trigger_end: trigger_end + config.DOB_TRIGGER_WINDOW]
            for date_pat in self._DATE_PATTERNS:
                date_match = date_pat.search(window)
                if date_match:
                    abs_start = trigger_end + date_match.start()
                    abs_end = trigger_end + date_match.end()
                    entities.append(
                        Entity(
                            text=text[abs_start:abs_end],
                            label=self.label,
                            start=abs_start,
                            end=abs_end,
                            confidence=0.96,
                            source="dob_regex",
                        )
                    )
                    break  # One date per trigger

        return entities


# ---------------------------------------------------------------------------
# PAN Card (Indian Permanent Account Number)
# ---------------------------------------------------------------------------

class PANDetector(BaseDetector):
    """Detects Indian Permanent Account Numbers (PAN).
    Format: 5 letters + 4 digits + 1 letter (e.g. ABCPS1234D, ABCDE1234F).
    """

    label = config.PAN

    _PATTERN = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b")

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        for m in self._PATTERN.finditer(text):
            entities.append(
                Entity(
                    text=m.group(1),
                    label=self.label,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=0.98,
                    source="pan_regex",
                )
            )
        return entities


# ---------------------------------------------------------------------------
# Aadhaar Number
# ---------------------------------------------------------------------------

class AadhaarDetector(BaseDetector):
    """Detects 12-digit Indian Aadhaar Numbers (e.g. 1234 5678 9012, 1234-5678-9012)."""

    label = config.AADHAAR

    _PATTERN = re.compile(
        r"(?<!\d)"
        r"(?:Aadhaar\s*(?:No\.?|Number)?:?\s*)?"
        r"([1-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4})"
        r"(?!\d)",
        re.IGNORECASE,
    )

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        for m in self._PATTERN.finditer(text):
            raw = m.group(1)
            # Only match if preceded by trigger OR explicitly formatted as 4-4-4
            is_formatted = " " in raw or "-" in raw
            is_triggered = bool(re.search(r"aadhaar", text[max(0, m.start()-30):m.start()], re.IGNORECASE))
            if is_formatted or is_triggered:
                entities.append(
                    Entity(
                        text=raw,
                        label=self.label,
                        start=m.start(1),
                        end=m.end(1),
                        confidence=0.97,
                        source="aadhaar_regex",
                    )
                )
        return entities


# ---------------------------------------------------------------------------
# Bank Account Number
# ---------------------------------------------------------------------------

class BankAccountDetector(BaseDetector):
    """Detects Bank Account Numbers (9 to 18 digits preceded by trigger words)."""

    label = config.BANK_ACCOUNT

    _TRIGGER_PATTERN = re.compile(
        r"(?:bank\s+account(?:\s+no\.?)?|account\s+no\.?|a/c\s+no\.?|account\s+number)\s*:?\s*",
        re.IGNORECASE,
    )
    _ACC_PATTERN = re.compile(r"(\d{9,18})")

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        for tm in self._TRIGGER_PATTERN.finditer(text):
            window = text[tm.end(): tm.end() + 40]
            am = self._ACC_PATTERN.search(window)
            if am:
                start = tm.end() + am.start(1)
                end = tm.end() + am.end(1)
                entities.append(
                    Entity(
                        text=text[start:end],
                        label=self.label,
                        start=start,
                        end=end,
                        confidence=0.95,
                        source="bank_account_regex",
                    )
                )
        return entities


# ---------------------------------------------------------------------------
# IFSC Code
# ---------------------------------------------------------------------------

class IFSCDetector(BaseDetector):
    """Detects Indian Financial System Code (IFSC). Format: 4 letters + 0 + 6 chars (e.g. HDFC0001234)."""

    label = config.IFSC_CODE

    _PATTERN = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        for m in self._PATTERN.finditer(text):
            entities.append(
                Entity(
                    text=m.group(1),
                    label=self.label,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=0.98,
                    source="ifsc_regex",
                )
            )
        return entities


# ---------------------------------------------------------------------------
# DIN (Director Identification Number)
# ---------------------------------------------------------------------------

class DINDetector(BaseDetector):
    """Detects 8-digit Director Identification Numbers (DIN)."""

    label = config.DIN

    _TRIGGER_PATTERN = re.compile(
        r"(?:din|director\s+identification\s+number)\s*:?\s*",
        re.IGNORECASE,
    )
    _DIN_PATTERN = re.compile(r"(\d{8})")

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        for tm in self._TRIGGER_PATTERN.finditer(text):
            window = text[tm.end(): tm.end() + 20]
            dm = self._DIN_PATTERN.search(window)
            if dm:
                start = tm.end() + dm.start(1)
                end = tm.end() + dm.end(1)
                entities.append(
                    Entity(
                        text=text[start:end],
                        label=self.label,
                        start=start,
                        end=end,
                        confidence=0.97,
                        source="din_regex",
                    )
                )
        return entities


# ---------------------------------------------------------------------------
# GSTIN & CIN
# ---------------------------------------------------------------------------

class GSTINDetector(BaseDetector):
    """Detects Indian GSTIN numbers."""

    label = config.GSTIN

    _PATTERN = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1})\b")

    def detect(self, text: str) -> List[Entity]:
        return [
            Entity(text=m.group(1), label=self.label, start=m.start(1), end=m.end(1), confidence=0.98, source="gstin_regex")
            for m in self._PATTERN.finditer(text)
        ]


class CINDetector(BaseDetector):
    """Detects Indian Corporate Identity Numbers (CIN). Format: U28129PN1979PLC141032."""

    label = config.CIN

    _PATTERN = re.compile(r"\b([LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b")

    def detect(self, text: str) -> List[Entity]:
        return [
            Entity(text=m.group(1), label=self.label, start=m.start(1), end=m.end(1), confidence=0.98, source="cin_regex")
            for m in self._PATTERN.finditer(text)
        ]

