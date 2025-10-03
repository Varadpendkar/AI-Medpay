# bill_buster.py
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.ocr_processor import ocr_from_image_bytes

AMOUNT_RE = re.compile(r"(?P<amount>\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?)")  # crude


def normalize_amount(s: Optional[str]) -> float:
    if not s:
        return 0.0
    s2 = s.replace(',', '').replace(' ', '')
    try:
        return float(s2)
    except Exception:
        s3 = re.sub(r'[^\d\.]', '', s2)
        try:
            return float(s3) if s3 else 0.0
        except Exception:
            return 0.0


def parse_text_lines(raw_text: str) -> List[Dict[str, Any]]:
    """
    Very simple line-by-line parser:
    - For each non-empty line, find the last monetary-looking token as amount
    - Leading part is description, capture optional date
    - Returns: list of { line_id, description, amount, date, raw_line }
    """
    lines = raw_text.splitlines()
    parsed: List[Dict[str, Any]] = []
    lid = 1
    for ln in lines:
        ln = (ln or '').strip()
        if not ln:
            continue
        amounts = AMOUNT_RE.findall(ln)
        if not amounts:
            continue
        amt = amounts[-1]
        amt_val = normalize_amount(amt)
        parts = re.split(re.escape(amt), ln, maxsplit=1)
        desc = (parts[0] if parts else ln).strip()
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})|(\d{2}/\d{2}/\d{4})', ln)
        date_val = None
        if date_match:
            date_text = date_match.group(0)
            try:
                if '-' in date_text:
                    date_val = datetime.strptime(date_text, "%Y-%m-%d").date().isoformat()
                else:
                    date_val = datetime.strptime(date_text, "%d/%m/%Y").date().isoformat()
            except Exception:
                date_val = None
        parsed.append({
            "line_id": lid,
            "description": desc[:200],
            "raw_line": ln,
            "amount": round(amt_val, 2),
            "date": date_val,
        })
        lid += 1
    return parsed


def parse_bill_file(file_storage=None, text: Optional[str] = None, tesseract_cmd: Optional[str] = None) -> Dict[str, Any]:
    """
    Accept a Flask FileStorage or raw text and return a result dict:
    { status, raw_text, parsed_items, errors }
    """
    raw_text = ""
    errors: List[str] = []

    if file_storage is not None:
        # consume file bytes
        b = file_storage.read()
        text_from_ocr, err = ocr_from_image_bytes(b, tesseract_cmd=tesseract_cmd)
        if text_from_ocr:
            raw_text = text_from_ocr
        else:
            if err:
                errors.append(f"OCR failed: {err}")
            try:
                raw_text = b.decode('utf-8', errors='ignore')
            except Exception:
                raw_text = ""
    elif text:
        raw_text = text
    else:
        return {"status": "error", "message": "no file or text provided", "parsed_items": [], "errors": ["no_input"]}

    parsed_items = parse_text_lines(raw_text or "")
    return {"status": "ok", "raw_text": raw_text, "parsed_items": parsed_items, "errors": errors}
