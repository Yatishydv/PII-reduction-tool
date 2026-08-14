"""
ner_detector.py — spaCy-based NER for PERSON and ORG entities.

Uses the en_core_web_sm model (loaded once at instantiation).

Design notes:
- PERSON entities: confidence boosted if followed by a title keyword
  (Director, Manager, etc.) within a small window.
- ORG entities: validated against org-suffix patterns.
- Both are suppressed if they match email/phone patterns
  (those are better handled by regex detectors).
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from .base import BaseDetector, Entity
from .. import config

logger = logging.getLogger(__name__)


# Compiled org-suffix pattern (used to validate ORG and demote PERSON→ORG)
_ORG_SUFFIX_RE = re.compile(
    r"(?:" + "|".join(config.ORG_SUFFIX_PATTERNS) + r")",
    re.IGNORECASE,
)

# Compiled person-title suffix pattern
_PERSON_TITLE_SUFFIX_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in config.PERSON_TITLE_SUFFIXES) + r")\b",
    re.IGNORECASE,
)

# Compiled person-title prefix pattern
_PERSON_TITLE_PREFIX_RE = re.compile(
    r"(?:" + "|".join(re.escape(t) for t in config.PERSON_TITLE_PREFIXES) + r")\s+",
    re.IGNORECASE,
)

# Compiled person context labels
_PERSON_CONTEXT_RE = re.compile(
    r"(?:" + "|".join(re.escape(t) for t in config.PERSON_CONTEXT_LABELS) + r")\s*",
    re.IGNORECASE,
)

# Email-like suffix — suppress entities that look like domains
_EMAIL_LIKE_RE = re.compile(r"@|\.com|\.in|\.org|\.net", re.IGNORECASE)


class NERDetector(BaseDetector):
    """Wrapper around spaCy NER for PERSON and ORG detection.

    Args:
        model_name: spaCy model to load (default: ``en_core_web_sm``).

    Raises:
        RuntimeError: If the spaCy model cannot be loaded.
    """

    label = config.PERSON  # Primary label; also produces config.ORG entities

    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        self._model_name = model_name
        self._nlp: Optional[object] = None
        self._cache = {}
        self._load_model()

    def _load_model(self) -> None:
        """Load the spaCy NLP model. Called once during initialisation."""
        try:
            import spacy  # type: ignore[import]
            self._nlp = spacy.load(self._model_name)
            logger.info("Loaded spaCy model: %s", self._model_name)
        except Exception as exc:
            logger.error("Failed to load spaCy model %r: %s", self._model_name, exc)
            raise RuntimeError(
                f"spaCy model '{self._model_name}' could not be loaded. "
                f"Run: python -m spacy download {self._model_name}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_org(text: str) -> bool:
        """Return True if *text* matches an org-suffix pattern."""
        return bool(_ORG_SUFFIX_RE.search(text))

    @staticmethod
    def _looks_like_email(text: str) -> bool:
        return bool(_EMAIL_LIKE_RE.search(text))

    @staticmethod
    def _boost_person_confidence(text: str, surrounding: str) -> float:
        """Return a confidence boost for PERSON if contextual cues match."""
        base = 0.75
        if _PERSON_TITLE_SUFFIX_RE.search(surrounding):
            base += 0.15
        if _PERSON_CONTEXT_RE.search(surrounding):
            base += 0.10
        if _PERSON_TITLE_PREFIX_RE.match(text.strip()):
            base += 0.05
        return min(base, 1.0)

    def detect(self, text: str) -> List[Entity]:
        """Detect PERSON and ORG entities in *text*.

        Returns a combined list of :class:`Entity` objects labelled
        either ``config.PERSON`` or ``config.ORG``.
        """
        if self._nlp is None:  # pragma: no cover
            return []

        text_stripped = text.strip()
        if not text_stripped:
            return []

        # Check cache for repetitive table cells & short texts
        if len(text_stripped) < 200 and text_stripped in self._cache:
            return [
                Entity(
                    text=e.text,
                    label=e.label,
                    start=e.start,
                    end=e.end,
                    confidence=e.confidence,
                    source=e.source
                )
                for e in self._cache[text_stripped]
            ]

        doc = self._nlp(text)
        entities: List[Entity] = []

        for ent in doc.ents:
            span_text = ent.text.strip()

            # Skip very short spans (single chars, lone digits)
            if len(span_text) < 3:
                continue

            # Skip if it looks like an email/URL
            if self._looks_like_email(span_text):
                continue

            # CRITICAL FILTER: Skip if span text is a known financial / prospectus term (e.g. Offer, Equity, Bids)
            clean_lower = span_text.lower().strip()
            if clean_lower in config.NON_PII_STOPWORDS:
                continue
            # Also skip if every word in span is a stopword (e.g. Equity Shares, Promoter Selling Shareholders)
            words = clean_lower.split()
            if all(w in config.NON_PII_STOPWORDS for w in words):
                continue

            if ent.label_ == "PERSON":
                # Strict PERSON validation:
                # 1. Skip if contains digits (e.g. ISO 9001:2015, C-101, 7,559.52)
                if any(ch.isdigit() for ch in span_text):
                    continue
                # 2. Skip if any word is a known non-PII stopword or location
                if any(w in config.NON_PII_STOPWORDS for w in words):
                    continue
                # 3. Skip if contains punctuation like slashes, parentheses, colons, numbers
                if any(c in span_text for c in ["/", "(", ")", ":", "=", "+", "%", "&"]):
                    continue
                # 4. Check if it should be reclassified as ORG
                if self._looks_like_org(span_text):
                    label = config.ORG
                    conf = 0.80
                    src = "ner_org_reclassified"
                else:
                    label = config.PERSON
                    # Surrounding context: 80 chars before the entity
                    surrounding = text[max(0, ent.start_char - 80): ent.end_char + 80]
                    conf = self._boost_person_confidence(span_text, surrounding)
                    src = "ner_person"

            elif ent.label_ in ("ORG", "COMPANY", "GPE"):
                # Only keep entities that look like actual organisations
                if ent.label_ == "GPE":
                    # GPE = Geopolitical entity (city/country) — skip unless org suffix
                    if not self._looks_like_org(span_text):
                        continue
                label = config.ORG
                conf = 0.80
                src = "ner_org"

            else:
                continue  # Other spaCy labels (DATE, MONEY, etc.) are not our concern

            entities.append(
                Entity(
                    text=span_text,
                    label=label,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=conf,
                    source=src,
                )
            )

        if len(text_stripped) < 200:
            self._cache[text_stripped] = entities

        return entities
