"""
metrics.py — Precision, Recall, F1, and Accuracy calculations.

Implements entity-level evaluation with exact-span matching.

Matching rule:
  A predicted entity is a True Positive if:
    1. Its label matches the gold annotation label, AND
    2. Its text (stripped) matches the gold annotation text (stripped,
       case-insensitive for emails/phones, exact otherwise).

This is conservative (exact-match) and is clearly documented.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MetricsResult:
    """Container for evaluation metrics."""
    label: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def precision(self) -> float:
        if self.tp + self.fp == 0:
            return 0.0
        return self.tp / (self.tp + self.fp)

    @property
    def recall(self) -> float:
        if self.tp + self.fn == 0:
            return 0.0
        return self.tp / (self.tp + self.fn)

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)

    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.fn + self.tn
        if total == 0:
            return 0.0
        return (self.tp + self.tn) / total

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "TP": self.tp,
            "FP": self.fp,
            "FN": self.fn,
            "TN": self.tn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "accuracy": round(self.accuracy, 4),
        }


def _normalize(text: str, label: str) -> str:
    """Normalize text for matching."""
    text = text.strip()
    # Case-insensitive for email, phone, ip
    if label.upper() in ("EMAIL", "PHONE", "IP_ADDRESS", "SSN", "CREDIT_CARD"):
        text = text.lower()
    return text


def compute_metrics(
    gold_annotations: List[dict],
    predictions: List[dict],
    labels: Optional[List[str]] = None,
) -> Dict[str, MetricsResult]:
    """Compute per-label and overall metrics.

    Args:
        gold_annotations: List of ``{"text": ..., "label": ...}`` dicts.
        predictions:      List of ``{"text": ..., "label": ...}`` dicts.
        labels:           Optional list of labels to include (default: all seen).

    Returns:
        A dict mapping label → :class:`MetricsResult`, plus key "OVERALL".

    Matching rule:
        A prediction is a TP if there exists a gold annotation with the
        same label and the same normalized text.
        Unmatched predictions are FP; unmatched gold annotations are FN.
        TN = estimated as the number of non-PII tokens not falsely flagged
             (set to 0 where not calculable from annotation format).
    """
    # Collect all labels
    all_labels: set[str] = set()
    for item in gold_annotations + predictions:
        all_labels.add(item["label"].upper())
    if labels:
        all_labels = all_labels.union({l.upper() for l in labels})

    results: Dict[str, MetricsResult] = {lbl: MetricsResult(label=lbl) for lbl in all_labels}
    results["OVERALL"] = MetricsResult(label="OVERALL")

    # Build gold sets per label: {label: {normalized_text}}
    gold_sets: Dict[str, set[str]] = {}
    for ann in gold_annotations:
        lbl = ann["label"].upper()
        gold_sets.setdefault(lbl, set()).add(_normalize(ann["text"], lbl))

    # Build gold multisets (to handle duplicates correctly)
    gold_remaining: Dict[str, List[str]] = {}
    for ann in gold_annotations:
        lbl = ann["label"].upper()
        gold_remaining.setdefault(lbl, []).append(_normalize(ann["text"], lbl))

    pred_remaining: Dict[str, List[str]] = {}
    for pred in predictions:
        lbl = pred["label"].upper()
        pred_remaining.setdefault(lbl, []).append(_normalize(pred["text"], lbl))

    # Count TP, FP, FN per label
    for lbl in all_labels:
        gold_list = list(gold_remaining.get(lbl, []))
        pred_list = list(pred_remaining.get(lbl, []))

        tp = 0
        for p in pred_list:
            if p in gold_list:
                tp += 1
                gold_list.remove(p)  # Each gold consumed only once

        fp = len(pred_list) - tp
        fn = len(gold_remaining.get(lbl, []))  - tp

        results[lbl].tp = tp
        results[lbl].fp = max(fp, 0)
        results[lbl].fn = max(fn, 0)

        results["OVERALL"].tp += tp
        results["OVERALL"].fp += max(fp, 0)
        results["OVERALL"].fn += max(fn, 0)

    return results
