"""
evaluator.py — Loads annotation datasets, runs the detector, and computes metrics.

Two evaluation datasets are used:
1. gold_annotations.json  — Hand-annotated entities from the actual Red Herring Prospectus.
2. synthetic_cases.json   — Known-ground-truth test cases for SSN, CC, DOB, IP, etc.

The evaluator runs detection on each text snippet, compares predictions
against gold annotations using exact-match, and computes TP/FP/FN.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .metrics import compute_metrics, MetricsResult

logger = logging.getLogger(__name__)


class Evaluator:
    """Runs evaluation against annotated datasets.

    Args:
        redactor: A :class:`~src.redaction.redactor.Redactor` instance.
        gold_path: Path to ``gold_annotations.json``.
        synthetic_path: Path to ``synthetic_cases.json``.
    """

    def __init__(
        self,
        redactor,
        gold_path: str | Path,
        synthetic_path: str | Path,
    ) -> None:
        self._redactor = redactor
        self._gold_path = Path(gold_path)
        self._synthetic_path = Path(synthetic_path)
        self._gold_data: List[dict] = []
        self._synthetic_data: List[dict] = []
        self._load_data()

    def _load_data(self) -> None:
        if self._gold_path.exists():
            with open(self._gold_path, "r", encoding="utf-8") as f:
                self._gold_data = json.load(f)
            logger.info("Loaded %d gold annotations", len(self._gold_data))
        else:
            logger.warning("Gold annotations not found: %s", self._gold_path)

        if self._synthetic_path.exists():
            with open(self._synthetic_path, "r", encoding="utf-8") as f:
                self._synthetic_data = json.load(f)
            logger.info("Loaded %d synthetic cases", len(self._synthetic_data))
        else:
            logger.warning("Synthetic cases not found: %s", self._synthetic_path)

    def _run_detector_on_cases(self, cases: List[dict]) -> tuple[List[dict], List[dict]]:
        """Run detector on each case and return (gold_list, pred_list).

        Each case has format:
            {"text": "...", "label": "...", "context": "..."}
        where `context` is the full text containing the PII,
        and `text` + `label` identify the expected entity.

        If no `context` is present, uses `text` directly.
        """
        gold_list: List[dict] = []
        pred_list: List[dict] = []

        for case in cases:
            context = case.get("context", case.get("text", ""))
            gold_text = case.get("text", "")
            gold_label = case.get("label", "UNKNOWN").upper()

            # Run detector on the context text
            entities = self._redactor.detect(context)

            # Record gold
            gold_list.append({"text": gold_text, "label": gold_label})

            # Record predictions
            for ent in entities:
                pred_list.append({"text": ent.text, "label": ent.label.upper()})

        return gold_list, pred_list

    def evaluate_gold(self) -> Dict[str, MetricsResult]:
        """Evaluate against the gold (real-document) annotations."""
        if not self._gold_data:
            logger.warning("No gold data to evaluate")
            return {}
        gold_list, pred_list = self._run_detector_on_cases(self._gold_data)
        return compute_metrics(gold_list, pred_list)

    def evaluate_synthetic(self) -> Dict[str, MetricsResult]:
        """Evaluate against synthetic test cases."""
        if not self._synthetic_data:
            logger.warning("No synthetic data to evaluate")
            return {}
        gold_list, pred_list = self._run_detector_on_cases(self._synthetic_data)
        return compute_metrics(gold_list, pred_list)

    def evaluate_all(self) -> Dict[str, Dict[str, MetricsResult]]:
        """Run both evaluations and return combined results."""
        return {
            "gold": self.evaluate_gold(),
            "synthetic": self.evaluate_synthetic(),
        }

    def get_false_positives(self, cases: List[dict]) -> List[dict]:
        """Return cases where the detector predicted PII that was not annotated."""
        fps: List[dict] = []
        for case in cases:
            context = case.get("context", case.get("text", ""))
            gold_text = case.get("text", "").strip().lower()
            gold_label = case.get("label", "UNKNOWN").upper()
            entities = self._redactor.detect(context)
            for ent in entities:
                if ent.text.strip().lower() != gold_text or ent.label.upper() != gold_label:
                    fps.append({
                        "context": context[:100],
                        "predicted_text": ent.text,
                        "predicted_label": ent.label,
                        "gold_text": gold_text,
                        "gold_label": gold_label,
                    })
        return fps

    def get_false_negatives(self, cases: List[dict]) -> List[dict]:
        """Return cases where the detector missed an annotated entity."""
        fns: List[dict] = []
        for case in cases:
            context = case.get("context", case.get("text", ""))
            gold_text = case.get("text", "").strip().lower()
            gold_label = case.get("label", "UNKNOWN").upper()
            entities = self._redactor.detect(context)
            matched = any(
                ent.text.strip().lower() == gold_text and ent.label.upper() == gold_label
                for ent in entities
            )
            if not matched:
                fns.append({
                    "gold_text": gold_text,
                    "gold_label": gold_label,
                    "context": context[:100],
                    "detected": [{"text": e.text, "label": e.label} for e in entities],
                })
        return fns
