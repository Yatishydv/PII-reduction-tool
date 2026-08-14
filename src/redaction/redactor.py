"""
redactor.py — Orchestrates the full detection → replacement pipeline.

Pipeline:
1. Receive plain text (from a paragraph or table cell).
2. Run all detectors in sequence.
3. Resolve overlaps.
4. Return the redacted text and the list of entities detected.

The Redactor does NOT handle DOCX file I/O — that is the responsibility
of DocxProcessor. This module only operates on strings so it can be
tested independently.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from .. import config
from ..detectors.base import Entity
from ..detectors.entity_resolver import EntityResolver
from .replacement import ReplacementGenerator

logger = logging.getLogger(__name__)


class Redactor:
    """Applies all PII detectors to a text string and returns redacted output.

    Args:
        detectors: List of :class:`BaseDetector` instances to run.
        generator: :class:`ReplacementGenerator` instance for fake data.
        resolver:  :class:`EntityResolver` for overlap resolution.

    Example::

        redactor = Redactor(detectors=[EmailDetector(), PhoneDetector()],
                            generator=ReplacementGenerator())
        redacted, entities = redactor.redact("Call john@example.com on +91 9876543210")
    """

    def __init__(
        self,
        detectors: list,
        generator: ReplacementGenerator,
        resolver: EntityResolver | None = None,
    ) -> None:
        self._detectors = detectors
        self._generator = generator
        self._resolver = resolver or EntityResolver()

    def detect(self, text: str) -> List[Entity]:
        """Run all detectors and return resolved entities.

        Args:
            text: Plain text to analyse.

        Returns:
            Non-overlapping list of :class:`Entity` objects.
        """
        stripped = text.strip()
        if not stripped or len(stripped) < 3:
            return []

        # Fast-Path Check: Skip if text is pure number / percentage / currency amount / table dash
        # Examples: "100.00", "50.5%", "1,250.00", "₹7,100", "10", "-", "Nil"
        clean_text = stripped.lower().replace(",", "").replace("%", "").replace("₹", "").replace("rs.", "").strip()
        if clean_text.replace(".", "").replace("-", "").isdigit():
            return []

        if clean_text in config.NON_PII_STOPWORDS:
            return []

        all_entities: List[Entity] = []
        for detector in self._detectors:
            found = detector.detect(text)
            all_entities.extend(found)

        resolved = self._resolver.resolve(all_entities)
        return resolved

    def redact(self, text: str) -> Tuple[str, List[Entity]]:
        """Detect and replace all PII in *text*.

        Args:
            text: Input plain text.

        Returns:
            A tuple of (redacted_text, list_of_detected_entities).
            The redacted text has fake values substituted in place.
        """
        entities = self.detect(text)
        if not entities:
            return text, []

        # Build redacted text by processing entities in reverse order
        # (so that character offsets remain valid)
        result = text
        for entity in reversed(entities):
            fake = self._generator.get_replacement(entity.text, entity.label)
            result = result[: entity.start] + fake + result[entity.end:]
            logger.debug(
                "Replaced %s at [%d:%d] with synthetic value (len=%d)",
                entity.label,
                entity.start,
                entity.end,
                len(fake),
            )

        return result, entities

    def get_replacement_map(self) -> dict:
        """Return the full {(original, label): fake} mapping from the generator."""
        return self._generator.get_full_map()

    @property
    def generator(self) -> ReplacementGenerator:
        return self._generator
