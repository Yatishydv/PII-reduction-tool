"""
address_detector.py — Keyword-anchor based address detection.

Strategy:
---------
Physical addresses in Indian legal/financial documents (like the Red Herring
Prospectus) follow patterns such as:
    "11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka - Khed,
     Pune – 410 501, Maharashtra, India"

Detection algorithm:
1. Scan each text segment for address anchor keywords (Flat, Plot, Village, etc.).
2. Count how many distinct anchors appear within ADDRESS_CONTEXT_WINDOW chars.
3. If count >= ADDRESS_MIN_ANCHOR_HITS, extract the full address span.

The span is extended to capture the whole address block by looking for
sentence boundaries or line breaks.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from .base import BaseDetector, Entity
from .. import config

# Compiled anchor patterns
_ANCHOR_PATTERNS: List[re.Pattern] = [
    re.compile(pat, re.IGNORECASE) for pat in config.ADDRESS_ANCHORS
]

# PIN code pattern (6-digit Indian PIN)
_PINCODE_RE = re.compile(r"[–\-\s]\s*(\d{3}\s?\d{3})\b")

# Country/state suffixes that mark the end of an address
_ADDRESS_TERMINATORS_RE = re.compile(
    r"(maharashtra|india|madhya pradesh|karnataka|gujarat|rajasthan|"
    r"uttar pradesh|west bengal|telangana|tamil nadu|andhra pradesh)"
    r"[,.\s]*(?:india)?",
    re.IGNORECASE,
)


def _find_anchor_hits(text: str) -> List[Tuple[int, int]]:
    """Return list of (start, end) positions of anchor matches in *text*."""
    hits: List[Tuple[int, int]] = []
    for pattern in _ANCHOR_PATTERNS:
        for m in pattern.finditer(text):
            hits.append((m.start(), m.end()))
    # Sort by position
    hits.sort(key=lambda x: x[0])
    return hits


def _extract_address_span(text: str, anchor_start: int, anchor_end: int) -> Tuple[int, int]:
    """
    Given an anchor position, expand backward (to start of the address) and
    forward (to end of the address block, typically marked by city/state/country).

    Returns (span_start, span_end) in absolute character offsets.
    """
    # Walk backward to find start: stop at newline, semicolon, or common delimiters
    backward_limit = max(0, anchor_start - 150)
    preceding = text[backward_limit:anchor_start]
    # Find the last sentence-ending character
    for sep in ["\n", ";", ":", ".", "•"]:
        idx = preceding.rfind(sep)
        if idx != -1:
            backward_limit = backward_limit + idx + 1
            break

    # Walk forward to find end: look for state/country or double-newline
    forward_limit = min(len(text), anchor_end + config.ADDRESS_CONTEXT_WINDOW)
    remainder = text[anchor_end:forward_limit]

    span_end = forward_limit
    # Look for terminator (Maharashtra, India, etc.)
    term_m = _ADDRESS_TERMINATORS_RE.search(remainder)
    if term_m:
        span_end = anchor_end + term_m.end()
    else:
        # Fallback: stop at first double-newline or semicolon
        for sep in ["\n\n", ";\n", "\n"]:
            idx = remainder.find(sep)
            if idx != -1:
                span_end = anchor_end + idx
                break

    span_start = max(0, backward_limit)
    return span_start, min(span_end, len(text))


_PLAIN_ADDRESS_KEYWORDS = [
    "flat", "apartment", "apt", "floor", "plot", "survey", "village",
    "taluka", "taluk", "district", "lane", "road", "nagar", "society",
    "colony", "building", "bungalow", "pincode", "postal", "mumbai",
    "pune", "maharashtra", "bengaluru", "bangalore", "marg", "chowk",
    "sector", "block", "pin",
]

class AddressDetector(BaseDetector):
    """Keyword-anchor based physical address detector.

    Detects multi-component addresses by counting how many distinct address
    anchor keywords appear in a sliding window. Produces one Entity per
    detected address span.
    """

    label = config.ADDRESS

    def detect(self, text: str) -> List[Entity]:
        entities: List[Entity] = []
        if not text or len(text) < 15:
            return entities

        text_lower = text.lower()
        if not any(kw in text_lower for kw in _PLAIN_ADDRESS_KEYWORDS):
            return entities

        hits = _find_anchor_hits(text)

        if len(hits) < config.ADDRESS_MIN_ANCHOR_HITS:
            return entities

        # Group hits that are within ADDRESS_CONTEXT_WINDOW of each other
        processed_spans: List[Tuple[int, int]] = []
        i = 0
        while i < len(hits):
            cluster_start = hits[i][0]
            cluster_end = hits[i][1]
            j = i + 1
            hit_count = 1

            # Expand cluster while hits are within the window
            while j < len(hits) and hits[j][0] - cluster_start <= config.ADDRESS_CONTEXT_WINDOW:
                cluster_end = max(cluster_end, hits[j][1])
                hit_count += 1
                j += 1

            if hit_count >= config.ADDRESS_MIN_ANCHOR_HITS:
                # Extract the full address span around this cluster
                span_start, span_end = _extract_address_span(text, cluster_start, cluster_end)

                # Check this doesn't heavily overlap with an already processed span
                overlaps_existing = any(
                    not (span_end <= ps or span_start >= pe)
                    for ps, pe in processed_spans
                )
                if not overlaps_existing and span_end > span_start:
                    address_text = text[span_start:span_end].strip()
                    if len(address_text) >= 20:  # Discard trivially short spans
                        processed_spans.append((span_start, span_end))
                        entities.append(
                            Entity(
                                text=address_text,
                                label=self.label,
                                start=span_start,
                                end=span_end,
                                confidence=0.75,
                                source="address_keyword",
                            )
                        )

            i = j if j > i else i + 1

        return entities
