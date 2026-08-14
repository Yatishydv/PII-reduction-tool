"""Detector sub-package."""
from .base import BaseDetector, Entity
from .regex_detectors import (
    EmailDetector, PhoneDetector, IPDetector,
    SSNDetector, CreditCardDetector, DOBDetector,
)
from .ner_detector import NERDetector
from .address_detector import AddressDetector
from .entity_resolver import EntityResolver

__all__ = [
    "BaseDetector", "Entity",
    "EmailDetector", "PhoneDetector", "IPDetector",
    "SSNDetector", "CreditCardDetector", "DOBDetector",
    "NERDetector", "AddressDetector", "EntityResolver",
]
