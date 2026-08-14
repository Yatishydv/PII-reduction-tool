"""
entity_resolver.py — Overlap resolution and final entity consolidation.

After all detectors run, the combined entity list may contain:
- Duplicate detections of the same span
- Overlapping spans (e.g., an email inside an address block)
- Sub-spans (e.g., a name within a larger name)

This module applies a greedy, priority-ordered overlap resolution.

Priority order (higher = wins in overlap):
  EMAIL > PHONE > IP_ADDRESS > SSN > CREDIT_CARD > DOB > PERSON > ORG > ADDRESS

Rationale: Regex-based detectors are more precise for structured PII;
NER is more ambiguous; ADDRESS is the broadest and most likely to contain
other PII sub-spans.
"""
from __future__ import annotations

import logging
from typing import List

from .base import Entity
from .. import config

logger = logging.getLogger(__name__)

# Label priority: lower number = higher priority (wins in overlap)
_PRIORITY: dict[str, int] = {
    config.EMAIL: 1,
    config.PHONE: 2,
    config.IP_ADDRESS: 3,
    config.SSN: 4,
    config.CREDIT_CARD: 5,
    config.DOB: 6,
    config.PERSON: 7,
    config.ORG: 8,
    config.ADDRESS: 9,
}

_DEFAULT_PRIORITY = 99


def _priority(entity: Entity) -> int:
    return _PRIORITY.get(entity.label, _DEFAULT_PRIORITY)


class EntityResolver:
    """Resolves overlapping entities from multiple detectors.

    Algorithm:
    1. Sort entities by (start, -span_length, priority).
    2. Greedily select non-overlapping entities.
       - When two entities overlap, keep the one with higher priority
         (lower priority number).
       - Among equal priorities, prefer the longer span.
    3. Return the resolved list sorted by start position.
    """

    def resolve(self, entities: List[Entity]) -> List[Entity]:
        """Return a non-overlapping, resolved list of entities.

        Args:
            entities: Combined output from all detectors (may overlap).

        Returns:
            Deduplicated, non-overlapping entities sorted by start offset.
        """
        # Filter out false positives from NON_PII_STOPWORDS
        filtered_ents: List[Entity] = []
        for e in entities:
            txt_lower = e.text.strip().lower()
            if txt_lower in config.NON_PII_STOPWORDS:
                continue
            words = txt_lower.split()
            if all(w in config.NON_PII_STOPWORDS for w in words):
                continue
            
            # Additional strict filtering for PERSON label
            if e.label == config.PERSON:
                if any(ch.isdigit() for ch in e.text):
                    continue
                if any(w in config.NON_PII_STOPWORDS for w in words):
                    continue
                if any(c in e.text for c in ["/", "(", ")", ":", "=", "+", "%", "&"]):
                    continue

            filtered_ents.append(e)

        if not filtered_ents:
            return []

        # Sort: by start, then longer span first, then higher priority
        sorted_ents = sorted(
            filtered_ents,
            key=lambda e: (e.start, -(e.end - e.start), _priority(e)),
        )

        resolved: List[Entity] = []
        for candidate in sorted_ents:
            overlapping = [e for e in resolved if e.overlaps(candidate)]
            if not overlapping:
                resolved.append(candidate)
            else:
                # Check if candidate has higher priority than ALL overlapping
                if all(_priority(candidate) < _priority(e) for e in overlapping):
                    # Remove lower-priority overlaps and add candidate
                    for e in overlapping:
                        resolved.remove(e)
                    resolved.append(candidate)
                # Otherwise: skip candidate (existing entities take precedence)

        resolved.sort(key=lambda e: e.start)
        logger.debug("EntityResolver: %d → %d entities after resolution", len(entities), len(resolved))
        return resolved

    def deduplicate_by_text(self, entities: List[Entity]) -> List[Entity]:
        """Remove exact-text duplicates, keeping highest-confidence entity.

        Useful for cross-paragraph deduplication before building the
        replacement map.
        """
        seen: dict[tuple[str, str], Entity] = {}
        for ent in entities:
            key = (ent.text.strip().lower(), ent.label)
            if key not in seen or ent.confidence > seen[key].confidence:
                seen[key] = ent
        return list(seen.values())
