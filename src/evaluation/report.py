"""
report.py — Markdown evaluation report generator.

Writes a structured, human-readable evaluation_report.md from
the output of the Evaluator.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .metrics import MetricsResult


_REPORT_TEMPLATE = """\
# PII Redaction Tool — Evaluation Report

*Generated: {timestamp}*

---

## 1. Objective

Evaluate the precision, recall, F1-score, and accuracy of the hybrid PII
redaction system applied to (a) a hand-annotated subset of the actual Red
Herring Prospectus, and (b) a synthetic test dataset covering PII types
that may not appear naturally in the source document.

---

## 2. Dataset

### 2.1 Gold Annotations (Real Document)

| Field | Value |
|-------|-------|
| Source document | Red Herring Prospectus.docx (KSH International Limited) |
| Annotation method | Manual review of document content |
| Total annotations | {gold_count} |
| PII types covered | PERSON, EMAIL, PHONE, ORG, ADDRESS |

### 2.2 Synthetic Test Dataset

| Field | Value |
|-------|-------|
| Total synthetic cases | {synthetic_count} |
| PII types covered | SSN, CREDIT_CARD, DOB, IP_ADDRESS, PERSON, EMAIL, PHONE |

---

## 3. PII Categories

| Category | Required by Assignment | Detection Method |
|----------|----------------------|-----------------|
| PERSON | ✅ | spaCy NER + contextual heuristics |
| EMAIL | ✅ | Regex (RFC-5321 pattern) |
| PHONE | ✅ | Regex (Indian/international formats) |
| ORG | ✅ | spaCy NER + org-suffix validation |
| ADDRESS | ✅ | Keyword-anchor heuristic |
| SSN | ✅ | Regex (NNN-NN-NNNN pattern) |
| CREDIT_CARD | ✅ | Regex + Luhn algorithm |
| DOB | ✅ | Context-anchored regex |
| IP_ADDRESS | ✅ | Regex with octet validation |

---

## 4. Gold Standard Construction

Gold annotations were created by manually reviewing paragraphs and tables
in the Red Herring Prospectus document. Each annotation records the exact
PII text span and its label. Ambiguous cases (e.g., city names that appear
both as addresses and standalone) were excluded.

---

## 5. Synthetic Test Cases

Synthetic cases provide known ground truth for PII types (SSN, credit card,
DOB, IP) that do not appear naturally in the Red Herring Prospectus. Each
case provides a context string and the exact expected entity text and label.

---

## 6. Detection Pipeline

```
Text Input
   │
   ├── EmailDetector (regex)
   ├── PhoneDetector (regex + digit count validation)
   ├── IPDetector (regex + octet validation)
   ├── SSNDetector (regex)
   ├── CreditCardDetector (regex + Luhn)
   ├── DOBDetector (context-anchored regex)
   ├── NERDetector (spaCy en_core_web_sm → PERSON/ORG)
   └── AddressDetector (keyword-anchor heuristic)
         │
         ▼
   EntityResolver (greedy overlap resolution, priority-ordered)
         │
         ▼
   ReplacementGenerator (deterministic fake data)
```

---

## 7. Matching Methodology

**Exact-span match**: A prediction is a True Positive if:
1. Its `label` matches the gold annotation `label` (case-insensitive), AND
2. Its `text` (stripped, normalised) matches the gold annotation `text`.

For EMAIL, PHONE, IP_ADDRESS, SSN, CREDIT_CARD: comparison is
case-insensitive.

For PERSON, ORG, ADDRESS: comparison is case-insensitive after stripping.

Unmatched predictions are **False Positives**.
Unmatched gold annotations are **False Negatives**.

---

## 8. Confusion Matrix (Overall)

### 8.1 Gold Dataset

| Metric | Value |
|--------|-------|
| True Positives (TP) | {gold_tp} |
| False Positives (FP) | {gold_fp} |
| False Negatives (FN) | {gold_fn} |
| True Negatives (TN) | N/A (not calculable at entity level) |

### 8.2 Synthetic Dataset

| Metric | Value |
|--------|-------|
| True Positives (TP) | {syn_tp} |
| False Positives (FP) | {syn_fp} |
| False Negatives (FN) | {syn_fn} |
| True Negatives (TN) | N/A |

---

## 9. Overall Metrics

### 9.1 Gold Dataset

| Metric | Value |
|--------|-------|
| Precision | {gold_precision:.4f} |
| Recall | {gold_recall:.4f} |
| F1 Score | {gold_f1:.4f} |
| Accuracy (TP / (TP + FP + FN)) | {gold_accuracy:.4f} |

### 9.2 Synthetic Dataset

| Metric | Value |
|--------|-------|
| Precision | {syn_precision:.4f} |
| Recall | {syn_recall:.4f} |
| F1 Score | {syn_f1:.4f} |
| Accuracy (TP / (TP + FP + FN)) | {syn_accuracy:.4f} |

---

## 10. Per-Category Metrics (Gold Dataset)

{gold_per_category_table}

---

## 11. Per-Category Metrics (Synthetic Dataset)

{syn_per_category_table}

---

## 12. Observed False Positives

{false_positives_section}

---

## 13. Observed False Negatives

{false_negatives_section}

---

## 14. Limitations

1. **Address detection** is heuristic and may over- or under-span addresses.
   Multi-line addresses that lack recognisable keywords may be missed.

2. **NER for PERSON** relies on spaCy `en_core_web_sm` which has lower
   accuracy for Indian names compared to English names. Uncommon Indian
   names may be missed (false negatives).

3. **Merged-cell tables** in DOCX may cause duplicate processing of cells;
   the processor deduplicates by XML element ID to mitigate this.

4. **Hyperlinks**: The underlying `href` of hyperlinks is not modified
   (e.g., `mailto:` links). Display text is redacted.

5. **DOB**: Only context-anchored dates are redacted. An unmarked date of
   birth without a "DOB:" or "Date of Birth:" label will not be detected.

6. **Cross-run PII**: PII that spans multiple DOCX runs (e.g., an email split
   across two runs by formatting) is handled by merging all runs in a
   paragraph, but complex nested formatting may be partially lost.

7. **IPv6** is not supported.

---

## 15. Future Improvements

1. Use `en_core_web_lg` or a fine-tuned Indian-language NER model for
   higher PERSON/ORG recall.
2. Add PAN, Aadhaar, DIN, and GSTIN detectors for Indian-specific IDs.
3. Implement multi-paragraph address detection across adjacent paragraphs.
4. Add semantic similarity-based name deduplication (same person, different
   spelling).
5. Use a confidence threshold UI to allow users to tune precision/recall.
6. Fine-tune DOB detection to handle more diverse date formats.

---

## 16. Reproducibility

```bash
# Clone repository and install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Run redaction
python -m src.main \\
    --input "Red Herring Prospectus.docx" \\
    --output redacted_output.docx

# Run evaluation
python -m src.main --evaluate \\
    --gold-annotations evaluation/gold_annotations.json \\
    --synthetic-cases evaluation/synthetic_cases.json

# Run tests
pytest tests/ -v
```
"""


def _build_per_category_table(results: Dict[str, MetricsResult]) -> str:
    """Build a markdown table from per-label metrics."""
    headers = ["Label", "TP", "FP", "FN", "Precision", "Recall", "F1"]
    rows = [headers, ["-" * len(h) for h in headers]]

    for label, m in sorted(results.items()):
        if label == "OVERALL":
            continue
        rows.append([
            label,
            str(m.tp),
            str(m.fp),
            str(m.fn),
            f"{m.precision:.4f}",
            f"{m.recall:.4f}",
            f"{m.f1:.4f}",
        ])

    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def _build_fp_section(fps: List[dict]) -> str:
    if not fps:
        return "No significant false positives observed in the evaluated dataset."
    lines = ["| Context | Predicted | Expected |", "| ------- | --------- | -------- |"]
    for fp in fps[:10]:
        ctx = fp.get("context", "")[:60].replace("|", "\\|")
        pred = f"{fp.get('predicted_text','')[:30]} ({fp.get('predicted_label','')})"
        exp = f"{fp.get('gold_text','')[:30]} ({fp.get('gold_label','')})"
        lines.append(f"| {ctx} | {pred} | {exp} |")
    return "\n".join(lines)


def _build_fn_section(fns: List[dict]) -> str:
    if not fns:
        return "No false negatives observed in the evaluated dataset."
    lines = ["| Gold Text | Gold Label | Context |", "| --------- | ---------- | ------- |"]
    for fn in fns[:10]:
        ctx = fn.get("context", "")[:60].replace("|", "\\|")
        lines.append(
            f"| {fn.get('gold_text','')[:30]} | {fn.get('gold_label','')} | {ctx} |"
        )
    return "\n".join(lines)


class ReportGenerator:
    """Generates the evaluation_report.md file."""

    def __init__(
        self,
        gold_results: Dict[str, MetricsResult],
        synthetic_results: Dict[str, MetricsResult],
        gold_count: int,
        synthetic_count: int,
        false_positives: Optional[List[dict]] = None,
        false_negatives: Optional[List[dict]] = None,
    ) -> None:
        self._gold = gold_results
        self._syn = synthetic_results
        self._gold_count = gold_count
        self._synthetic_count = synthetic_count
        self._fps = false_positives or []
        self._fns = false_negatives or []

    def write(self, output_path: str | Path) -> Path:
        """Write the evaluation report to *output_path*."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        gold_overall = self._gold.get("OVERALL", MetricsResult("OVERALL"))
        syn_overall = self._syn.get("OVERALL", MetricsResult("OVERALL"))

        content = _REPORT_TEMPLATE.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            gold_count=self._gold_count,
            synthetic_count=self._synthetic_count,
            gold_tp=gold_overall.tp,
            gold_fp=gold_overall.fp,
            gold_fn=gold_overall.fn,
            syn_tp=syn_overall.tp,
            syn_fp=syn_overall.fp,
            syn_fn=syn_overall.fn,
            gold_precision=gold_overall.precision,
            gold_recall=gold_overall.recall,
            gold_f1=gold_overall.f1,
            gold_accuracy=gold_overall.accuracy,
            syn_precision=syn_overall.precision,
            syn_recall=syn_overall.recall,
            syn_f1=syn_overall.f1,
            syn_accuracy=syn_overall.accuracy,
            gold_per_category_table=_build_per_category_table(self._gold),
            syn_per_category_table=_build_per_category_table(self._syn),
            false_positives_section=_build_fp_section(self._fps),
            false_negatives_section=_build_fn_section(self._fns),
        )

        out.write_text(content, encoding="utf-8")
        return out
