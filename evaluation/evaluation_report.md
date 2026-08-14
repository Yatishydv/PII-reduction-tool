# PII Redaction Tool — Evaluation Report

*Generated: 2026-08-14 00:16:02*

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
| Total annotations | 26 |
| PII types covered | PERSON, EMAIL, PHONE, ORG, ADDRESS |

### 2.2 Synthetic Test Dataset

| Field | Value |
|-------|-------|
| Total synthetic cases | 22 |
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
| True Positives (TP) | 23 |
| False Positives (FP) | 6 |
| False Negatives (FN) | 3 |
| True Negatives (TN) | N/A (not calculable at entity level) |

### 8.2 Synthetic Dataset

| Metric | Value |
|--------|-------|
| True Positives (TP) | 21 |
| False Positives (FP) | 6 |
| False Negatives (FN) | 1 |
| True Negatives (TN) | N/A |

---

## 9. Overall Metrics

### 9.1 Gold Dataset

| Metric | Value |
|--------|-------|
| Precision | 0.7931 |
| Recall | 0.8846 |
| F1 Score | 0.8364 |
| Accuracy (TP / (TP + FP + FN)) | 0.7188 |

### 9.2 Synthetic Dataset

| Metric | Value |
|--------|-------|
| Precision | 0.7778 |
| Recall | 0.9545 |
| F1 Score | 0.8571 |
| Accuracy (TP / (TP + FP + FN)) | 0.7500 |

---

## 10. Per-Category Metrics (Gold Dataset)

| Label | TP | FP | FN | Precision | Recall | F1 |
| ----- | -- | -- | -- | --------- | ------ | -- |
| EMAIL | 8 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| ORG | 4 | 3 | 1 | 0.5714 | 0.8000 | 0.6667 |
| PERSON | 5 | 2 | 2 | 0.7143 | 0.7143 | 0.7143 |
| PHONE | 6 | 1 | 0 | 0.8571 | 1.0000 | 0.9231 |

---

## 11. Per-Category Metrics (Synthetic Dataset)

| Label | TP | FP | FN | Precision | Recall | F1 |
| ----- | -- | -- | -- | --------- | ------ | -- |
| CREDIT_CARD | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| DOB | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| EMAIL | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| IP_ADDRESS | 3 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| ORG | 2 | 6 | 0 | 0.2500 | 1.0000 | 0.4000 |
| PERSON | 4 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| PHONE | 2 | 0 | 1 | 1.0000 | 0.6667 | 0.8000 |
| SSN | 2 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

---

## 12. Observed False Positives

| Context | Predicted | Expected |
| ------- | --------- | -------- |
| Contact Person: Sarthak Malvadkar, Company Secretary and Com | + 91 20 4505 3237 (PHONE) | sarthak malvadkar (PERSON) |
| Rohit Kushal Hegde, Joint Managing Director | Joint (ORG) | rohit kushal hegde (PERSON) |
| Rakhi Girija Shetty, Whole-time Director | Rakhi Girija Shetty (ORG) | rakhi girija shetty (PERSON) |
| Dinesh Hirachand Munot, Independent Director | Dinesh Hirachand Munot (ORG) | dinesh hirachand munot (PERSON) |
| Contact Person: Sarthak Malvadkar, Company Secretary and Com | Sarthak Malvadkar (PERSON) | + 91 20 4505 3237 (PHONE) |
| ICICI Securities Limited, ICICI Centre, H.T. Parekh Marg, Ch | Parekh Marg (PERSON) | icici securities limited (ORG) |
| Employee SSN: 123-45-6789 as per HR records. | SSN (ORG) | 123-45-6789 (SSN) |
| Social Security Number: 987-65-4321 | Social Security Number (ORG) | 987-65-4321 (SSN) |
| Payment card on file: 4111 1111 1111 1111 (Visa) | Visa (ORG) | 4111 1111 1111 1111 (CREDIT_CARD) |
| MasterCard ending in: 5500-0000-0000-0004 | MasterCard (ORG) | 5500-0000-0000-0004 (CREDIT_CARD) |

---

## 13. Observed False Negatives

| Gold Text | Gold Label | Context |
| --------- | ---------- | ------- |
| rakhi girija shetty | PERSON | Rakhi Girija Shetty, Whole-time Director |
| dinesh hirachand munot | PERSON | Dinesh Hirachand Munot, Independent Director |
| icici securities limited | ORG | ICICI Securities Limited, ICICI Centre, H.T. Parekh Marg, Ch |
| +1 212 555 1234 | PHONE | US contact number: +1 212 555 1234 |

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
python -m src.main \
    --input "Red Herring Prospectus.docx" \
    --output redacted_output.docx

# Run evaluation
python -m src.main --evaluate \
    --gold-annotations evaluation/gold_annotations.json \
    --synthetic-cases evaluation/synthetic_cases.json

# Run tests
pytest tests/ -v
```
