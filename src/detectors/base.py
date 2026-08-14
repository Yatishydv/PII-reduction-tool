"""
base.py — Abstract base class for all PII detectors.

Any new detector (e.g., PAN, PASSPORT) must inherit from BaseDetector
and implement the `detect(text)` method.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List


@dataclass
class Entity:
    """A single detected PII entity.

    Attributes:
        text:       The exact text span that was detected.
        label:      PII type label (e.g., "EMAIL", "PERSON").
        start:      Start character offset in the source text.
        end:        End character offset in the source text.
        confidence: Detection confidence in [0.0, 1.0].
        source:     Which detector produced this entity.
    """
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0
    source: str = "unknown"

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Entity(label={self.label!r}, text={self.text!r}, "
            f"start={self.start}, end={self.end}, conf={self.confidence:.2f})"
        )

    def overlaps(self, other: "Entity") -> bool:
        """Return True if this entity overlaps with *other*."""
        return self.start < other.end and other.start < self.end

    def contains(self, other: "Entity") -> bool:
        """Return True if this entity wholly contains *other*."""
        return self.start <= other.start and self.end >= other.end

    def span_length(self) -> int:
        return self.end - self.start


class BaseDetector(abc.ABC):
    """Abstract base class for all PII detectors.

    Sub-class and implement ``detect(text)`` to add a new PII type.

    Example::

        class PANDetector(BaseDetector):
            label = "PAN"
            _PATTERN = re.compile(r'[A-Z]{5}\\d{4}[A-Z]')

            def detect(self, text: str) -> List[Entity]:
                return [
                    Entity(m.group(), self.label, m.start(), m.end(), source="pan_regex")
                    for m in self._PATTERN.finditer(text)
                ]
    """

    #: Must be overridden in subclass to set the PII label.
    label: str = "UNKNOWN"

    @abc.abstractmethod
    def detect(self, text: str) -> List[Entity]:
        """Detect PII entities in *text*.

        Args:
            text: Plain text to analyse.

        Returns:
            A (possibly empty) list of :class:`Entity` objects.
        """
        ...

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}(label={self.label!r})"
