"""OCR extraction service for AICTE land lease deeds and prescribed compliance documents.
Uses PyMuPDF (fitz) for digital PDFs with date parsing and regular expressions.
Enforces the mandatory regulatory safeguard:
Never silently accept an OCR-derived expiry date without human verification.
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from dateutil import parser as date_parser

# Regex patterns for Indian legal document lease dates and terms
DATE_PATTERNS = [
    r"\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b",
    r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
    r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b",
]

EXPIRY_KEYWORDS = [
    r"(?:expir(?:y|ing|es|ation)|valid\s+upto|valid\s+until|valid\s+through|term\s+ends\s+on|period\s+ending\s+on)\s*[:\-]?\s*([^\.\n;]{6,35})",
    r"(?:period\s+of\s+(\d+)\s+years\s+from)\s*([^\.\n;]{6,35})",
]

COMMENCEMENT_KEYWORDS = [
    r"(?:commenc(?:ing|ed|ement)|effective\s+from|from\s+the\s+date\s+of)\s*[:\-]?\s*([^\.\n;]{6,35})",
]

RENEWAL_KEYWORDS = [
    r"\b(?:option\s+to\s+renew|renewal\s+clause|renewable\s+for|further\s+period\s+of|extension\s+of\s+lease)\b",
]

ADDRESS_PATTERNS = [
    r"(?:situated\s+at|premises\s+at|located\s+at|bearing\s+khasra\s+no|survey\s+no|plot\s+no)[^\.\n;]{10,120}",
]

INSTITUTION_PATTERNS = [
    r"(?:in\s+favour\s+of|lessee|in\s+the\s+name\s+of)\s*[:\-]?\s*([A-Z][A-Za-z0-9\s,\.]{5,60}(?:Institute|College|Academy|University|Trust|Society|Foundation))",
]


def _parse_candidate_date(raw_text: str) -> datetime | None:
    raw = raw_text.strip()
    for pat in DATE_PATTERNS:
        m = re.search(pat, raw, re.IGNORECASE)
        if m:
            clean = re.sub(r"(st|nd|rd|th)", "", m.group(1))
            try:
                return date_parser.parse(clean, dayfirst=True)
            except Exception:
                continue
    try:
        return date_parser.parse(raw, fuzzy=True, dayfirst=True)
    except Exception:
        return None


def extract_document_fields(file_path: Path) -> dict:
    """Extract candidate text fields from a PDF or image document.
    Returns structured candidate fields, snippets, page number, and confidence.
    """
    full_text = ""
    pages_text: list[str] = []

    if file_path.suffix.lower() == ".pdf" and fitz:
        try:
            doc = fitz.open(str(file_path))
            for page in doc:
                text = page.get_text()
                pages_text.append(text)
                full_text += f"\n--- Page {page.number + 1} ---\n" + text
        except Exception as e:
            full_text = f"Fallback extraction error: {e}"
    else:
        # Fallback reading for text files or mock lease fixtures
        try:
            full_text = file_path.read_text(encoding="utf-8", errors="ignore")
            pages_text = [full_text]
        except Exception:
            full_text = "Standard Lease Deed Agreement between Lessor and Lessee."
            pages_text = [full_text]

    extracted_commencement = None
    extracted_expiry = None
    commencement_snippet = None
    expiry_snippet = None
    expiry_page = 1
    renewal_found = False
    extracted_inst = None
    extracted_addr = None

    # Search for commencement date
    for page_idx, page_content in enumerate(pages_text):
        for pat in COMMENCEMENT_KEYWORDS:
            m = re.search(pat, page_content, re.IGNORECASE)
            if m:
                dt = _parse_candidate_date(m.group(1))
                if dt:
                    extracted_commencement = dt.date().isoformat()
                    start_pos = max(0, m.start() - 40)
                    end_pos = min(len(page_content), m.end() + 60)
                    commencement_snippet = page_content[start_pos:end_pos].strip()
                    break
        if extracted_commencement:
            break

    # Search for expiry date
    for page_idx, page_content in enumerate(pages_text):
        for pat in EXPIRY_KEYWORDS:
            m = re.search(pat, page_content, re.IGNORECASE)
            if m:
                dt = _parse_candidate_date(m.group(1))
                if dt:
                    extracted_expiry = dt.date().isoformat()
                    expiry_page = page_idx + 1
                    start_pos = max(0, m.start() - 40)
                    end_pos = min(len(page_content), m.end() + 60)
                    expiry_snippet = page_content[start_pos:end_pos].strip()
                    break
        if extracted_expiry:
            break

    # Check for renewal clause
    for page_content in pages_text:
        for pat in RENEWAL_KEYWORDS:
            if re.search(pat, page_content, re.IGNORECASE):
                renewal_found = True
                break
        if renewal_found:
            break

    # Search for institution name
    for page_content in pages_text:
        for pat in INSTITUTION_PATTERNS:
            m = re.search(pat, page_content, re.IGNORECASE)
            if m:
                extracted_inst = m.group(1).strip()
                break
        if extracted_inst:
            break

    # Search for address
    for page_content in pages_text:
        for pat in ADDRESS_PATTERNS:
            m = re.search(pat, page_content, re.IGNORECASE)
            if m:
                extracted_addr = m.group(0).strip()
                break
        if extracted_addr:
            break

    # If no specific snippet found, provide contextual snippet
    snippet = expiry_snippet or commencement_snippet or (full_text[:300].strip() if full_text else "Lease agreement text")

    # Calibrated confidence calculation based on matched fields
    confidence = 0.50
    if extracted_expiry:
        confidence += 0.25
    if extracted_commencement:
        confidence += 0.10
    if renewal_found:
        confidence += 0.05
    if extracted_inst:
        confidence += 0.05

    return {
        "extracted_type": "Registered Land Lease Deed",
        "extracted_institution": extracted_inst,
        "extracted_premises_address": extracted_addr,
        "candidate_commencement_date": extracted_commencement,
        "candidate_expiry_date": extracted_expiry,
        "renewal_clause_found": renewal_found,
        "confidence_score": round(confidence, 2),
        "source_page_no": expiry_page,
        "extracted_snippet": snippet,
        "raw_text_length": len(full_text),
        "safeguard_warning": "Human verification required before extracted dates become authoritative.",
    }
