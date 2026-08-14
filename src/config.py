"""
config.py — Central configuration for the PII Redaction Tool.

All thresholds, patterns, and constants live here so they can be tuned
without touching the detection/replacement logic.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# PII type labels (string constants used throughout the codebase)
# ---------------------------------------------------------------------------
PERSON = "PERSON"
EMAIL = "EMAIL"
PHONE = "PHONE"
ORG = "ORG"
ADDRESS = "ADDRESS"
SSN = "SSN"
CREDIT_CARD = "CREDIT_CARD"
DOB = "DOB"
IP_ADDRESS = "IP_ADDRESS"

# Indian-specific & financial PII categories
PAN = "PAN"
AADHAAR = "AADHAAR"
BANK_ACCOUNT = "BANK_ACCOUNT"
IFSC_CODE = "IFSC_CODE"
DIN = "DIN"
GSTIN = "GSTIN"
CIN = "CIN"

ALL_PII_TYPES: list[str] = [
    PERSON, EMAIL, PHONE, ORG, ADDRESS, SSN, CREDIT_CARD, DOB, IP_ADDRESS,
    PAN, AADHAAR, BANK_ACCOUNT, IFSC_CODE, DIN, GSTIN, CIN,
]

# ---------------------------------------------------------------------------
# Detection thresholds
# ---------------------------------------------------------------------------
NER_PERSON_CONFIDENCE_THRESHOLD: float = 0.0   # spaCy sm doesn't give scores; use entity type
NER_ORG_CONFIDENCE_THRESHOLD: float = 0.0
ADDRESS_MIN_ANCHOR_HITS: int = 2               # Min keyword hits to classify as address
ADDRESS_CONTEXT_WINDOW: int = 300              # Characters window for address detection

# ---------------------------------------------------------------------------
# DOB: contextual triggers (must appear within this many chars before date)
# ---------------------------------------------------------------------------
DOB_TRIGGER_WINDOW: int = 60  # characters
DOB_TRIGGERS: list[str] = [
    "date of birth", "d.o.b.", "dob", "born on", "birth date",
    "date of birth:", "d.o.b.:", "dob:", "born:", "birthdate",
]

# ---------------------------------------------------------------------------
# Address keyword anchors
# ---------------------------------------------------------------------------
ADDRESS_ANCHORS: list[str] = [
    r"\bflat\b", r"\bapartment\b", r"\bapt\b", r"\bfloor\b",
    r"\bplot\b", r"\bplot\s+no\b", r"\bs\.?\s*no\b", r"\bsurvey\s+no\b",
    r"\bvillage\b", r"\btaluka\b", r"\btaluk\b", r"\bdistrict\b",
    r"\blane\b", r"\broad\b", r"\bnagar\b", r"\bsociety\b",
    r"\bcolony\b", r"\bbuilding\b", r"\bbungalow\b", r"\bpincode\b",
    r"\bpin\b", r"\bpin\s*code\b", r"\bpostal\b",
    r"\bmumbai\b", r"\bpune\b", r"\bmaharashtra\b", r"\bbengaluru\b", r"\bbangalore\b",
    r"\bmarg\b", r"\bchowk\b", r"\bsector\b", r"\bblock\b",
]

# Indian city list for address reinforcement (conservative subset)
INDIAN_CITIES: set[str] = {
    "pune", "mumbai", "delhi", "bengaluru", "bangalore", "chennai",
    "hyderabad", "kolkata", "ahmedabad", "surat", "bhopal", "nagpur",
    "nashik", "thane", "aurangabad", "raigad", "navi mumbai", "gurugram", "noida",
}

# ---------------------------------------------------------------------------
# Organization suffix patterns — entities ending in these are treated as ORG
# ---------------------------------------------------------------------------
ORG_SUFFIX_PATTERNS: list[str] = [
    r"\blimited\b", r"\bltd\.?\b", r"\bprivate limited\b", r"\bpvt\.?\s*ltd\.?\b",
    r"\bllp\b", r"\bllc\b", r"\bcorporation\b", r"\bcorp\.?\b",
    r"\bbank\b", r"\bsecurities\b", r"\bmanagement\b",
    r"\bassociates\b", r"\bservices\b", r"\bindustries\b",
    r"\benterprises\b", r"\bfoundation\b", r"\btrust\b",
]

# ---------------------------------------------------------------------------
# Title words that suggest the nearby text is a PERSON name
# ---------------------------------------------------------------------------
PERSON_TITLE_SUFFIXES: list[str] = [
    "director", "managing director", "chairman", "ceo", "cfo", "cto",
    "president", "manager", "officer", "compliance officer", "secretary",
    "promoter", "shareholder", "auditor", "partner", "company secretary",
    "executive", "joint managing director", "whole-time director",
    "independent director", "key managerial personnel", "kmp",
]

PERSON_TITLE_PREFIXES: list[str] = [
    "mr.", "mrs.", "ms.", "dr.", "prof.", "shri", "smt.", "cs", "ca",
]

# Non-PII financial, location, document, and prospectus terms that must NEVER be classified as PERSON or ORG
NON_PII_STOPWORDS: set[str] = {
    # Financial terms & offer terms
    "offer", "offers", "offering", "pre-offer", "bid", "bids", "bidding", "bidders", "bidder",
    "equity", "equity shares", "share", "shares", "face value", "fresh issue", "cap price", "floor price",
    "prospectus", "red herring prospectus", "rhp", "drhp", "draft prospectus", "price", "bid amount",
    "issue", "issuer", "issuance", "company", "companies", "promoter", "promoters", "promoter trusts",
    "the promoter selling shareholders", "promoter selling shareholders", "selling shareholders", "selling shareholder",
    "director", "directors", "board", "board of directors", "member", "members", "key managerial", "key managerial personnel", "kmp",
    "auditor", "auditors", "secretary", "compliance", "officer", "officers", "registrar", "registered broker",
    "section", "act", "table", "page", "schedule", "schedule xiii", "annexure", "part", "form", "clause", "clause(s)",
    "inr", "rs", "rs.", "rupees", "lakh", "lakhs", "crore", "crores", "million", "billion",
    "total", "net", "gross", "amount", "price", "value", "cost", "fee", "tax", "taxes", "tax deducted", "pat cagr", "pat margin",
    "period", "year", "fiscal", "fy", "fy2025", "fy2024", "quarter", "q1", "q2", "q3", "q4",
    "date", "dated", "day", "month", "march", "december", "january", "february", "april",
    "particulars", "description", "details", "summary", "index", "note", "notes", "bill", "expiry",
    "statement", "report", "financial", "information", "general", "capital", "risks", "acknowledgement slip",
    "individual bidders", "qib bidders", "wilful defaulter", "share transfer agents", "corrigenda thereto",
    "dp", "depository participant", "dp id", "bidder's dp id", "neft", "nro account", "upi bidders", "upi",
    "circuit kilometers", "gram jyoti", "gwh", "gigawatt-hour", "air conditioning", "mega volt-amperes", "megawatt",
    "pmay", "kisan urja suraksha", "photo voltaic", "kushal electricals", "challan", "non-gaap measures",
    "reference rate", "pursuant", "secondary transfer of", "excludes", "alpha", "brlm", "sebi", "sebi bhavan",
    "exchange(s)", "exchange(s", "exchange", "listing sebi bhavan", "mutual funds", "email", "parents branch",
    "rajesh branch", "sangeeta branch", "branch", "b. non-gaap measures", "c. operational", "operational",
    "widely circulated marathi daily newspaper", "marathi daily newspaper", "newspaper",

    # Locations, Cities, Roads & Buildings (MUST NEVER BE PERSON)
    "mumbai", "pune", "delhi", "bengaluru", "bangalore", "chennai", "hyderabad", "kolkata",
    "baner", "baner pune", "vikhroli", "kanjurmarg", "bandra", "bandra east", "bandra east mumbai",
    "bandra kurla complex", "deccan gymkhana", "shivaji nagar", "erandawane", "model colony",
    "chakan", "chakan taluka - khed", "chakan taluka-khed", "taluka-khed", "taluka khed", "khed",
    "taluka parner", "village khalumbre", "village", "khalumbre", "supa facility", "waterloo industrial",
    "waterloo industrial park", "waterloo industrial park ix", "appasaheb marathe marg,", "appasaheb marathe marg",
    "bapat marg", "marg backbay reclamation churchgate", "marg", "lane", "road", "road lane",
    "tara chambers", "kubera chambers opp", "sancheti hospital shivajinagar", "tanishq showroom",
    "buena monte", "pushpakamal apartment,", "pushpakamal apartment", "pushpakamal", "gopal house",
    "sharmila joshi website", "cherag gyara website", "soni website", "website",
}

# Person context labels in the document
PERSON_CONTEXT_LABELS: list[str] = [
    "contact person:", "name:", "promoter:", "director:", "shareholder:",
    "chairman:", "ceo:", "cfo:", "auditor:", "partner:", "compliance officer:",
    "company secretary:", "applicant:", "customer name:",
]

# ---------------------------------------------------------------------------
# Logging: whether to include redacted values in logs (set False for prod)
# ---------------------------------------------------------------------------
LOG_REDACTED_VALUES: bool = False  # Never log actual PII values
LOG_LEVEL: str = "INFO"
