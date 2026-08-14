"""
replacement.py — Deterministic fake-data generation for each PII type.

Key properties:
1. CONSISTENT: The same original value always maps to the same fake value
   within a single document run (maintained via an internal dictionary).
2. TYPE-APPROPRIATE: A PERSON is replaced with a PERSON, EMAIL with EMAIL, etc.
3. SYNTHETIC: All generated values are clearly fake; no real people's data used.
4. SEEDED: Uses a fixed random seed for reproducibility across runs.
"""
from __future__ import annotations

import hashlib
import re
import random
from typing import Dict, Optional

from faker import Faker

from .. import config

# Fixed seed for reproducibility
_SEED = 42
_faker_en = Faker("en_IN")      # Indian English locale for names/addresses
_faker_en.seed_instance(_SEED)
Faker.seed(_SEED)


def _deterministic_index(original: str, pool_size: int) -> int:
    """Return a stable integer index derived from *original* text hash.

    This ensures the same original always gets the same replacement,
    regardless of detection order.
    """
    digest = hashlib.md5(original.encode("utf-8"), usedforsecurity=False).hexdigest()
    return int(digest[:8], 16) % pool_size


# ---------------------------------------------------------------------------
# Fake-name pools (Indian first and last names for cultural consistency)
# ---------------------------------------------------------------------------
_FIRST_NAMES = [
    "Arjun", "Rohan", "Vikram", "Siddharth", "Aditya", "Rahul", "Nikhil",
    "Priya", "Ananya", "Divya", "Sneha", "Pooja", "Kritika", "Ritu",
    "Suresh", "Rajiv", "Manoj", "Deepak", "Sunita", "Kavita", "Geeta",
    "Omkar", "Gaurav", "Harish", "Meena", "Lakshmi", "Vijay", "Sumit",
    "Amit", "Kabir", "Tanvi", "Shreya", "Akash", "Kiran", "Ravi",
]

_LAST_NAMES = [
    "Mehta", "Sharma", "Patel", "Joshi", "Verma", "Iyer", "Nair",
    "Reddy", "Kumar", "Singh", "Gupta", "Shah", "Desai", "Rao",
    "Mishra", "Saxena", "Bose", "Chatterjee", "Das", "Mukherjee",
    "Pillai", "Menon", "Krishnamurthy", "Agarwal", "Chauhan", "Sinha",
    "Tiwari", "Dubey", "Thakur", "Yadav", "Pandey", "Malhotra", "Kapoor",
]

_MIDDLE_NAMES = [
    "Kumar", "Lal", "Prasad", "Raj", "Nath", "Devi", "Bai", "Rani",
    "Prakash", "Chandra", "Mohan", "Ram", "Babu", "Rajan",
]

# Synthetic company name components
_COMPANY_PREFIXES = [
    "Vertex", "Pinnacle", "Meridian", "Apex", "Summit", "Zenith",
    "Cascade", "Sterling", "Horizon", "Vanguard", "Paragon",
    "Matrix", "Nexus", "Synergy", "Catalyst", "Prism", "Luminary",
]
_COMPANY_SECTORS = [
    "Industrial", "Technologies", "Systems", "Solutions", "Enterprises",
    "Manufacturing", "Engineering", "International", "Global", "Dynamics",
]
_COMPANY_SUFFIXES = [
    "Limited", "Pvt. Ltd.", "LLP", "Corporation", "Associates",
    "Group", "Holdings",
]

# Fake city/address data
_FAKE_SOCIETIES = [
    "Sunrise Apartments", "Green Valley Society", "Blue Ridge Colony",
    "Lotus Park", "Harmony Towers", "Silver Oak Residency",
    "Royal Enclave", "Tulip Gardens", "Cedar Heights",
]
_FAKE_ROADS = [
    "12 Oak Lane", "47 Maple Road", "8/3 Elm Street", "Plot 22, Birch Avenue",
    "Flat 304, Pine Block", "Survey No. 99, Cedar Nagar",
]
_FAKE_CITIES = ["Indore", "Nagpur", "Nashik", "Vadodara", "Surat", "Bhopal", "Lucknow"]
_FAKE_STATES = ["Madhya Pradesh", "Gujarat", "Rajasthan", "Uttar Pradesh", "Haryana"]
_FAKE_PINS = ["453441", "400072", "411067", "380001", "302001", "462001", "226001"]


class ReplacementGenerator:
    """Generates and caches deterministic fake replacements for PII entities.

    Usage::

        gen = ReplacementGenerator()
        fake = gen.get_replacement("john.smith@example.com", "EMAIL")
        # Returns same value every time for same original+label

    The ``_map`` dictionary maps ``(original_text, label)`` → ``fake_text``
    and is populated lazily.
    """

    def __init__(self) -> None:
        # Mapping: (original_text, label) → fake_text
        self._map: Dict[tuple, str] = {}
        # Counters for sequential fake IDs (email, phone)
        self._email_counter = 1
        self._phone_counter = 1

    def get_replacement(self, original: str, label: str) -> str:
        """Return a consistent fake replacement for *original* with *label*.

        Args:
            original: The exact PII text to replace.
            label:    PII type label (e.g., ``"EMAIL"``, ``"PERSON"``).

        Returns:
            A synthetic fake string of the same type.
        """
        key = (original.strip(), label)
        if key not in self._map:
            self._map[key] = self._generate(original.strip(), label)
        return self._map[key]

    def get_full_map(self) -> Dict[tuple, str]:
        """Return a copy of the internal mapping (for logging/debugging)."""
        return dict(self._map)

    # ------------------------------------------------------------------
    # Internal generators — one per PII type
    # ------------------------------------------------------------------

    def _generate(self, original: str, label: str) -> str:
        generators = {
            config.PERSON: self._fake_person,
            config.EMAIL: self._fake_email,
            config.PHONE: self._fake_phone,
            config.ORG: self._fake_org,
            config.ADDRESS: self._fake_address,
            config.SSN: self._fake_ssn,
            config.CREDIT_CARD: self._fake_credit_card,
            config.DOB: self._fake_dob,
            config.IP_ADDRESS: self._fake_ip,
            config.PAN: self._fake_pan,
            config.AADHAAR: self._fake_aadhaar,
            config.BANK_ACCOUNT: self._fake_bank_account,
            config.IFSC_CODE: self._fake_ifsc,
            config.DIN: self._fake_din,
            config.GSTIN: self._fake_gstin,
            config.CIN: self._fake_cin,
        }
        gen = generators.get(label, self._generic_redact)
        return gen(original)

    def _fake_person(self, original: str) -> str:
        """Generate a realistic Indian full name."""
        parts = original.strip().split()
        idx_f = _deterministic_index(original + "_first", len(_FIRST_NAMES))
        idx_l = _deterministic_index(original + "_last", len(_LAST_NAMES))
        first = _FIRST_NAMES[idx_f]
        last = _LAST_NAMES[idx_l]
        if len(parts) >= 3:
            idx_m = _deterministic_index(original + "_mid", len(_MIDDLE_NAMES))
            return f"{first} {_MIDDLE_NAMES[idx_m]} {last}"
        return f"{first} {last}"

    def _fake_email(self, original: str) -> str:
        """Generate a synthetic email that looks realistic."""
        # Try to preserve local part structure
        match = re.match(r"([\w.+-]+)@", original.lower())
        if match:
            local_base = re.sub(r"[^a-z]", "", match.group(1))[:8] or "user"
        else:
            local_base = "user"
        idx = _deterministic_index(original, 9999)
        return f"{local_base}{idx:04d}@example-corp.com"

    def _fake_phone(self, original: str) -> str:
        """Generate a synthetic +91 phone number."""
        # Preserve country code format
        digits_only = re.sub(r"\D", "", original)
        if original.startswith("+91") or digits_only.startswith("91"):
            # Generate synthetic 10-digit mobile
            idx = _deterministic_index(original, 89999999)
            synthetic = 9000000001 + idx
            return f"+91 {str(synthetic)[:5]} {str(synthetic)[5:]}"
        else:
            idx = _deterministic_index(original, 8999999)
            return f"+91 90{idx:07d}"

    def _fake_org(self, original: str) -> str:
        """Generate a synthetic organisation name."""
        idx_p = _deterministic_index(original + "_prefix", len(_COMPANY_PREFIXES))
        idx_s = _deterministic_index(original + "_sector", len(_COMPANY_SECTORS))
        idx_sf = _deterministic_index(original + "_suffix", len(_COMPANY_SUFFIXES))

        # Detect original suffix (Limited, LLP, etc.) and preserve format
        orig_lower = original.lower()
        if "llp" in orig_lower:
            suffix = "LLP"
        elif "pvt" in orig_lower or "private" in orig_lower:
            suffix = "Pvt. Ltd."
        elif "limited" in orig_lower or "ltd" in orig_lower:
            suffix = "Limited"
        else:
            suffix = _COMPANY_SUFFIXES[idx_sf]

        return f"{_COMPANY_PREFIXES[idx_p]} {_COMPANY_SECTORS[idx_s]} {suffix}"

    def _fake_address(self, original: str) -> str:
        """Generate a synthetic Indian postal address."""
        idx_r = _deterministic_index(original + "_road", len(_FAKE_ROADS))
        idx_c = _deterministic_index(original + "_city", len(_FAKE_CITIES))
        idx_st = _deterministic_index(original + "_state", len(_FAKE_STATES))
        idx_p = _deterministic_index(original + "_pin", len(_FAKE_PINS))
        idx_soc = _deterministic_index(original + "_soc", len(_FAKE_SOCIETIES))
        return (
            f"{_FAKE_ROADS[idx_r]}, {_FAKE_SOCIETIES[idx_soc]}, "
            f"{_FAKE_CITIES[idx_c]} – {_FAKE_PINS[idx_p]}, "
            f"{_FAKE_STATES[idx_st]}, India"
        )

    @staticmethod
    def _fake_ssn(original: str) -> str:
        """Generate a syntactically valid but clearly synthetic SSN."""
        # Use deterministic digit manipulation
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        area = int(digest[0:3], 16) % 899 + 100   # 100–998, not 000 or 666
        if area in (000, 666):
            area = 500
        group = int(digest[3:5], 16) % 99 + 1     # 01–99
        serial = int(digest[5:9], 16) % 9999 + 1  # 0001–9999
        return f"{area:03d}-{group:02d}-{serial:04d}"

    @staticmethod
    def _fake_credit_card(original: str) -> str:
        """Return a well-known Luhn-valid test card number.

        We use the standard Visa test number 4111 1111 1111 1111.
        """
        # We vary only the last 4 digits deterministically
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        suffix = int(digest[:4], 16) % 9000 + 1000
        # Check which separator the original used
        sep = " " if " " in original else ("-" if "-" in original else "")
        # Use 4111 1111 1111 XXXX pattern (first 12 digits are Luhn-safe test prefix)
        base = f"4111{sep}1111{sep}1111{sep}{suffix}"
        return base

    @staticmethod
    def _fake_dob(original: str) -> str:
        """Generate a synthetic date string in a similar format."""
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        year = 1960 + int(digest[0:2], 16) % 40     # 1960–1999
        month = 1 + int(digest[2:4], 16) % 12
        day = 1 + int(digest[4:6], 16) % 28

        # Detect format from original
        if re.search(r"\d{4}-\d{2}-\d{2}", original):
            return f"{year:04d}-{month:02d}-{day:02d}"
        elif re.search(r"\d{1,2}/\d{1,2}/\d{4}", original):
            return f"{day:02d}/{month:02d}/{year:04d}"
        else:
            months_abbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return f"{day:02d} {months_abbr[month-1]} {year:04d}"

    @staticmethod
    def _fake_ip(original: str) -> str:
        """Generate a synthetic IPv4 address in the same /24 subnet."""
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        parts = original.split(".")
        try:
            a, b, c = int(parts[0]), int(parts[1]), int(parts[2])
        except (ValueError, IndexError):
            a, b, c = 10, 0, 0
        d = int(digest[0:2], 16) % 254 + 1   # 1–254
        return f"{a}.{b}.{c}.{d}"

    @staticmethod
    def _fake_pan(original: str) -> str:
        """Generate synthetic Indian PAN number (e.g. ABCPS1234D)."""
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        digits = int(digest[:4], 16) % 9000 + 1000
        return f"ABCPS{digits}D"

    @staticmethod
    def _fake_aadhaar(original: str) -> str:
        """Generate synthetic 12-digit Aadhaar number."""
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        part1 = 5000 + int(digest[:3], 16) % 4000
        part2 = 1000 + int(digest[3:6], 16) % 8999
        part3 = 1000 + int(digest[6:9], 16) % 8999
        sep = " " if " " in original else ("-" if "-" in original else "")
        return f"{part1}{sep}{part2}{sep}{part3}"

    @staticmethod
    def _fake_bank_account(original: str) -> str:
        """Generate synthetic bank account number."""
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        val = 5012345678901234 + (int(digest[:8], 16) % 1000000)
        return str(val)[:len(original.strip())]

    @staticmethod
    def _fake_ifsc(original: str) -> str:
        """Generate synthetic IFSC code."""
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        code = int(digest[:4], 16) % 9000 + 1000
        return f"HDFC000{code}"

    @staticmethod
    def _fake_din(original: str) -> str:
        """Generate synthetic 8-digit DIN."""
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        val = int(digest[:6], 16) % 90000000 + 10000000
        return str(val)

    @staticmethod
    def _fake_gstin(original: str) -> str:
        """Generate synthetic GSTIN."""
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        code = int(digest[:4], 16) % 9000 + 1000
        return f"27ABCDE{code}1Z5"

    @staticmethod
    def _fake_cin(original: str) -> str:
        """Generate synthetic CIN."""
        digest = hashlib.md5(original.encode(), usedforsecurity=False).hexdigest()
        code = int(digest[:6], 16) % 900000 + 100000
        return f"U28129PN1979PLC{code}"

    @staticmethod
    def _generic_redact(original: str) -> str:
        return "[REDACTED]"
