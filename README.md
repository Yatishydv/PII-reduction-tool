# PII Redaction Tool

**Scaler AI Labs — Environment Data Intern · Take-Home Assignment**

A production-quality, hybrid PII redaction system that processes real Microsoft Word (`.docx`) documents. Combines deterministic regex detectors with spaCy NER for comprehensive coverage of 9 PII categories.

---

## Assignment Summary

| Field | Value |
|-------|-------|
| Role | Environment Data Intern |
| Organisation | Scaler AI Labs |
| Source Document | Red Herring Prospectus.docx (KSH International Limited IPO) |
| Task | Detect and replace all PII with realistic fake data |
| Deadline | 12 August 2026, 12:00 PM |

---

## Results at a Glance

| Dataset | Precision | Recall | F1 |
|---------|-----------|--------|----|
| Gold (Real Document) | 0.793 | 0.885 | **0.836** |
| Synthetic Test Cases | 0.778 | 0.955 | **0.857** |

**Entities detected and replaced in source document:** `1,141`

| PII Type | Count |
|----------|-------|
| ORG (Company names) | 823 |
| PERSON (Names) | 238 |
| EMAIL | 43 |
| PHONE | 28 |
| ADDRESS | 9 |

---

## Architecture

```
Text Input
   │
   ├── EmailDetector          (regex, RFC-5321 compliant)
   ├── PhoneDetector          (regex, Indian & international formats)
   ├── IPDetector             (regex + octet range validation)
   ├── SSNDetector            (regex NNN-NN-NNNN, excludes 000/666)
   ├── CreditCardDetector     (regex + Luhn algorithm)
   ├── DOBDetector            (context-anchored regex, avoids financial dates)
   ├── NERDetector            (spaCy en_core_web_sm → PERSON / ORG)
   └── AddressDetector        (keyword-anchor heuristic for Indian addresses)
         │
         ▼
   EntityResolver             (greedy overlap resolution, label-priority ordered)
         │
         ▼
   ReplacementGenerator       (deterministic MD5-indexed fake data per type)
         │
         ▼
   DocxProcessor              (run-level replacement, formatting preserved)
```

### Key Design Decisions

1. **Regex for structured PII** — Email, phone, IP, SSN, credit card, DOB are deterministic regex matches. Much higher precision than NER for well-formatted strings.

2. **Luhn validation for credit cards** — Eliminates false positives on financial figures (₹7,100 → 16 digits but fails Luhn).

3. **Context-anchoring for DOB** — Only matches dates immediately preceded by "Date of Birth:", "DOB:", "D.O.B.:", "Born on:", etc. This prevents the 200+ financial year references in the prospectus from being redacted.

4. **NER + org-suffix validation** — spaCy PERSON/ORG labels are supplemented with suffix-based validation ("Limited", "LLP", "Pvt. Ltd.") to improve recall for Indian company names.

5. **Priority-ordered overlap resolution** — When detectors overlap (e.g., email within address block), a priority queue decides which entity wins: EMAIL > PHONE > IP > SSN > CC > DOB > PERSON > ORG > ADDRESS.

6. **Deterministic replacements** — The same original text always maps to the same fake value (via MD5 hash), so a person mentioned 50 times becomes the same fake name 50 times.

7. **Run-level DOCX processing** — Merges all formatting runs in a paragraph before detection, then distributes redacted text back into the first run. This handles PII split across multiple formatting runs.

---

## Evaluation

Evaluation uses two datasets:

### Gold Annotations (Real Document)
- 26 manually annotated PII entities from the Red Herring Prospectus
- Covers: PERSON, EMAIL, PHONE, ORG, ADDRESS
- Annotation method: Manual review of tables and body text

### Synthetic Dataset
- 22 programmatically created test cases with known ground truth
- Covers: EMAIL, PHONE, IP_ADDRESS, SSN, CREDIT_CARD, DOB, PERSON, ORG
- Provides ground truth for types not naturally in the source document

### Matching Rule
A prediction is a **True Positive** if:
1. `label` matches gold label (case-insensitive), AND
2. `text` (stripped, normalized) matches gold text (case-insensitive for EMAIL/PHONE/IP/SSN/CC)

### Per-Category Results (Gold)

| Label | TP | FP | FN | Precision | Recall | F1 |
|-------|----|----|----|-----------:|-------:|---:|
| EMAIL | 8 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| PHONE | 6 | 1 | 0 | 0.8571 | 1.0000 | **0.9231** |
| PERSON | 5 | 2 | 2 | 0.7143 | 0.7143 | **0.7143** |
| ORG | 4 | 3 | 1 | 0.5714 | 0.8000 | **0.6667** |
| **OVERALL** | **23** | **6** | **3** | **0.793** | **0.885** | **0.836** |

### Per-Category Results (Synthetic)

| Label | TP | FP | FN | Precision | Recall | F1 |
|-------|----|----|----|-----------:|-------:|---:|
| EMAIL | 3 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| PHONE | 2 | 0 | 1 | 1.0000 | 0.6667 | **0.8000** |
| IP_ADDRESS | 3 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| SSN | 2 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| CREDIT_CARD | 2 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| DOB | 3 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| PERSON | 4 | 0 | 0 | 1.0000 | 1.0000 | **1.0000** |
| ORG | 2 | 6 | 0 | 0.2500 | 1.0000 | **0.4000** |
| **OVERALL** | **21** | **6** | **1** | **0.778** | **0.955** | **0.857** |

---

## Project Structure

```
pii-redaction-tool/
├── src/
│   ├── __init__.py
│   ├── config.py                 ← Centralised constants, labels, thresholds
│   ├── main.py                   ← CLI entrypoint (redact + evaluate modes)
│   ├── docx_processor.py         ← DOCX reading/writing with run-level replacement
│   ├── detectors/
│   │   ├── base.py               ← BaseDetector interface + Entity dataclass
│   │   ├── regex_detectors.py    ← Email, Phone, IP, SSN, CreditCard, DOB
│   │   ├── ner_detector.py       ← spaCy PERSON + ORG detector
│   │   ├── address_detector.py   ← Keyword-anchor address detection
│   │   └── entity_resolver.py    ← Overlap resolution & deduplication
│   └── redaction/
│       ├── replacement.py        ← Deterministic fake-data generator
│       └── redactor.py           ← Pipeline orchestrator
├── api/
│   ├── app.py                    ← FastAPI application
│   └── static/
│       └── index.html            ← Web UI
├── evaluation/
│   ├── gold_annotations.json     ← 26 hand-annotated real-document PII
│   ├── synthetic_cases.json      ← 22 synthetic test cases
│   ├── evaluation_results.json   ← Machine-readable evaluation output
│   └── evaluation_report.md      ← Human-readable evaluation report
├── tests/
│   ├── conftest.py
│   ├── test_email.py
│   ├── test_phone.py
│   ├── test_ip.py
│   ├── test_ssn.py
│   ├── test_credit_card.py
│   ├── test_dob.py
│   ├── test_names.py
│   ├── test_addresses.py
│   ├── test_companies.py
│   └── test_integration.py
└── requirements.txt
```

---

## Setup and Usage

### Prerequisites
- Python 3.9+ (tested on 3.14.6)

### Installation

```bash
# Clone and navigate to project
cd pii-redaction-tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Redact a Document

```bash
python -m src.main --input "Red Herring Prospectus.docx" --output redacted_output.docx
```

**Options:**
- `--no-ner` — Disable spaCy NER (faster, regex-only, lower recall for names/orgs)
- `--save-map` — Save the original→fake replacement mapping to `replacement_map.json`
- `--verbose` / `-v` — Enable DEBUG logging

### Run Evaluation

```bash
python -m src.main --evaluate \
    --gold-annotations evaluation/gold_annotations.json \
    --synthetic-cases evaluation/synthetic_cases.json \
    --report-output evaluation/evaluation_report.md
```

### Run Tests

```bash
pytest tests/ -v
# Expected: 119 passed
```

### Start the API Server

```bash
cd api
uvicorn app:app --reload --port 8000
# Visit http://localhost:8000
```

---

## PII Detection Details

### Email
- **Method**: Regex `[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}`
- **Precision**: 1.00 (no false positives on financial numbers or CINs)

### Phone
- **Method**: Regex matching `+91`, ISD codes, 10+ digit sequences
- **Guard**: Minimum digit count filter eliminates 3–6 digit financial figures

### IP Address
- **Method**: Regex with per-octet range validation (0–255)
- **Guard**: Version strings like `3.8.13` rejected by octet validation

### SSN
- **Method**: Regex `NNN-NN-NNNN` with exclusion of `000` and `666` area codes

### Credit Card
- **Method**: Regex for 13–19 digit groups (space/hyphen separated) + **Luhn algorithm**
- **Key**: Luhn check eliminates financial figures that happen to have 16 digits

### Date of Birth
- **Method**: Context-anchored regex — only detects dates immediately after "DOB:", "Date of Birth:", "D.O.B.:", "Born on:", "birth date:", "birthdate:"
- **Key**: The prospectus has 200+ date references; context-anchoring is critical

### Person Names
- **Method**: spaCy `en_core_web_sm` PERSON entities, boosted by contextual triggers ("Director", "Mr.", "Ms.", "Contact Person:")
- **Limitation**: Indian names with uncommon spellings may be missed

### Organisation Names
- **Method**: spaCy ORG entities + suffix-based validation ("Limited", "LLP", "Pvt. Ltd.")
- **Known FP source**: In synthetic evaluation, ORG detector produces FPs from NER labelling text fragments as ORG entities

### Addresses
- **Method**: Keyword-anchor heuristic — minimum 2 of: Village, Taluka, Road, Plot, Flat, District, Pincode patterns, state names
- **Limitation**: Address spans are approximate; may over- or under-span

---

## Limitations (Documented)

1. **NER accuracy for Indian names** — `en_core_web_sm` is trained on English text; uncommon Indian names may produce false negatives. Solution: use `en_core_web_lg` or a fine-tuned Indian NLP model.

2. **Address boundaries** — Multi-line addresses that span multiple paragraphs are detected independently per paragraph. A multi-line address across paragraph boundaries may be only partially detected.

3. **Hyperlink hrefs** — The underlying `href` attribute of DOCX hyperlinks (e.g., `mailto:`) is not modified. Only the display text is redacted.

4. **Wide tables with duplicated content** — In very wide DOCX tables where the same contact information appears in every column (a formatting pattern in this document), the deduplication algorithm may miss some instances.

5. **IPv6** — Not supported.

6. **Split-run PII** — PII split across multiple formatting runs in the same paragraph is handled by run-merging, but complex hyperlinked runs may not be fully captured.

---

## Future Improvements

1. Fine-tune NER model on Indian financial documents for higher PERSON/ORG recall
2. Add Indian-specific PII types: PAN (`ABCDE1234F`), Aadhaar, DIN, GSTIN
3. Multi-paragraph address detection
4. Confidence threshold UI for precision/recall trade-off
5. Deploy as containerised service (Docker + Cloud Run)

---

## References

- spaCy documentation: https://spacy.io
- python-docx documentation: https://python-docx.readthedocs.io
- Faker library: https://faker.readthedocs.io
- Luhn algorithm: ISO/IEC 7812
- FastAPI: https://fastapi.tiangolo.com
