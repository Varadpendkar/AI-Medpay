"""
Bill Parser - Extract structured data from OCR results
Parses hospital bills to extract key fields and line items
"""
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime
from difflib import SequenceMatcher

LOG = logging.getLogger(__name__)


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings (0-1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def extract_hospital_name(text: str, words: List[str]) -> Optional[str]:
    """
    Extract hospital name from bill text
    Usually appears in first few lines with keywords like Hospital, Medical, Clinic
    """
    try:
        lines = text.split('\n')[:10]  # Check first 10 lines
        
        keywords = ['hospital', 'medical', 'clinic', 'healthcare', 'nursing', 'care']
        
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                # Clean up the line
                hospital = line.strip()
                # Remove common prefixes
                hospital = re.sub(r'^(bill|invoice|receipt|tax)\s+', '', hospital, flags=re.IGNORECASE)
                if len(hospital) > 5:  # Must be reasonable length
                    LOG.info(f"Extracted hospital name: {hospital}")
                    return hospital
        
        # Fallback: return first non-empty line
        for line in lines:
            clean = line.strip()
            if len(clean) > 5:
                return clean
        
        return "Unknown Hospital"
        
    except Exception as e:
        LOG.error(f"Error extracting hospital name: {e}")
        return "Unknown Hospital"


def extract_date(text: str) -> Optional[str]:
    """
    Extract bill date in YYYY-MM-DD format
    Looks for patterns like DD/MM/YYYY, DD-MM-YYYY, etc.
    """
    try:
        # Common date patterns
        patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2})',   # DD/MM/YY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',   # YYYY-MM-DD
            r'Date[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # Date: DD/MM/YYYY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Parse based on pattern
                if len(groups) == 3:
                    if len(groups[0]) == 4:  # YYYY-MM-DD
                        year, month, day = groups
                    elif len(groups[2]) == 4:  # DD/MM/YYYY
                        day, month, year = groups
                    else:  # DD/MM/YY
                        day, month, year = groups
                        year = f"20{year}" if int(year) < 50 else f"19{year}"
                    
                    # Validate and format
                    try:
                        date_obj = datetime(int(year), int(month), int(day))
                        formatted = date_obj.strftime('%Y-%m-%d')
                        LOG.info(f"Extracted date: {formatted}")
                        return formatted
                    except ValueError:
                        continue
        
        # Fallback to today's date
        return datetime.now().strftime('%Y-%m-%d')
        
    except Exception as e:
        LOG.error(f"Error extracting date: {e}")
        return datetime.now().strftime('%Y-%m-%d')


def extract_invoice_number(text: str) -> Optional[str]:
    """Extract invoice/bill number"""
    try:
        patterns = [
            r'(Invoice|Bill|Receipt)\s*(No|Number|#)?[:\s]*([A-Z0-9/-]+)',
            r'Bill\s*#?\s*:?\s*([A-Z0-9/-]+)',
            r'Invoice\s*:?\s*([A-Z0-9/-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_no = match.group(match.lastindex)
                if len(invoice_no) >= 3:  # Reasonable length
                    LOG.info(f"Extracted invoice number: {invoice_no}")
                    return invoice_no
        
        return "N/A"
        
    except Exception as e:
        LOG.error(f"Error extracting invoice number: {e}")
        return "N/A"


def extract_total_amount(text: str) -> float:
    """Extract total bill amount"""
    try:
        patterns = [
            r'(Total|Grand\s*Total|Amount\s*Due|Net\s*Amount)[:\s]*₹?\s*([\d,]+(?:\.\d{2})?)',
            r'Total[:\s]*Rs\.?\s*([\d,]+(?:\.\d{2})?)',
            r'₹\s*([\d,]+(?:\.\d{2})?)\s*\(Total\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(2).replace(',', '')
                amount = float(amount_str)
                LOG.info(f"Extracted total amount: ₹{amount}")
                return amount
        
        return 0.0
        
    except Exception as e:
        LOG.error(f"Error extracting total amount: {e}")
        return 0.0


def parse_line_items(ocr_result: Dict) -> List[Dict]:
    """
    Parse line items from OCR result
    Groups words by Y-coordinate to form table rows
    """
    try:
        words = ocr_result['words']
        boxes = ocr_result['boxes']
        
        if not words or not boxes:
            return []
        
        # Group words by Y-coordinate (±10px tolerance)
        rows = {}
        for i, box in enumerate(boxes):
            y = box['y']
            
            # Find existing row within tolerance
            found_row = None
            for row_y in rows.keys():
                if abs(y - row_y) < 10:
                    found_row = row_y
                    break
            
            if found_row is not None:
                rows[found_row].append((box['x'], words[i]))
            else:
                rows[y] = [(box['x'], words[i])]
        
        # Sort each row by X-coordinate (left to right)
        sorted_rows = []
        for y in sorted(rows.keys()):
            row_words = sorted(rows[y], key=lambda x: x[0])
            sorted_rows.append([word for _, word in row_words])
        
        # Identify table header row
        header_idx = None
        for i, row in enumerate(sorted_rows):
            row_text = ' '.join(row).lower()
            if 'description' in row_text or 'particulars' in row_text or 'item' in row_text:
                header_idx = i
                LOG.info(f"Found table header at row {i}: {row}")
                break
        
        if header_idx is None:
            LOG.warning("Could not find table header, parsing all rows")
            header_idx = 0
        
        # Parse line items from rows after header
        line_items = []
        for row in sorted_rows[header_idx + 1:]:
            if len(row) < 2:
                continue
            
            # Try to extract amount (last numeric column)
            amount = None
            qty = None
            unit_price = None
            
            for word in reversed(row):
                # Remove currency symbols and commas
                clean = word.replace('₹', '').replace('Rs', '').replace(',', '').strip()
                try:
                    val = float(clean)
                    if amount is None:
                        amount = val
                    elif unit_price is None:
                        unit_price = val
                    elif qty is None:
                        qty = int(val) if val == int(val) else val
                except ValueError:
                    continue
            
            if amount is not None and amount > 0:
                # Description is remaining words (excluding numeric values)
                desc_words = []
                for word in row:
                    clean = word.replace('₹', '').replace('Rs', '').replace(',', '').strip()
                    try:
                        float(clean)
                    except ValueError:
                        desc_words.append(word)
                
                description = ' '.join(desc_words).strip()
                
                if description:
                    line_items.append({
                        "desc": description,
                        "qty": qty or 1,
                        "unit": unit_price,
                        "amount": amount,
                        "code": None  # Can add CPT/ICD code extraction later
                    })
        
        LOG.info(f"Parsed {len(line_items)} line items")
        return line_items
        
    except Exception as e:
        LOG.exception(f"Error parsing line items: {e}")
        return []


def parse_bill(ocr_result: Dict) -> Dict:
    """
    Main parsing function - extract all structured data from OCR result
    
    Args:
        ocr_result: Output from ocr_utils.preprocess_and_ocr()
    
    Returns:
        Structured bill data with fields and line items
    """
    try:
        text = ocr_result['text']
        words = ocr_result['words']
        
        # Extract key fields
        hospital = extract_hospital_name(text, words)
        bill_date = extract_date(text)
        invoice_no = extract_invoice_number(text)
        
        # Parse line items
        line_items = parse_line_items(ocr_result)
        
        # Extract subtotal, GST, and grand total from line items
        subtotal = None
        gst = None
        total_amount = None
        
        for item in line_items:
            desc_lower = (item.get('desc') or '').lower()
            amount = item.get('amount', 0)
            
            if 'subtotal' in desc_lower or 'sub-total' in desc_lower or 'sub total' in desc_lower:
                subtotal = amount
            elif 'gst' in desc_lower or 'tax' in desc_lower or 'vat' in desc_lower:
                gst = amount
            elif 'grand total' in desc_lower or 'grandtotal' in desc_lower or 'total' in desc_lower:
                # Prefer "grand total" over just "total"
                if 'grand' in desc_lower or total_amount is None:
                    total_amount = amount
        
        # Fallback: if no total found in line items, try extract_total_amount
        if total_amount is None or total_amount == 0:
            total_amount = extract_total_amount(text)
        
        result = {
            "hospital": hospital,
            "bill_date": bill_date,
            "invoice_no": invoice_no,
            "total_amount": total_amount,
            "subtotal": subtotal,
            "gst": gst,
            "tax": gst,  # alias
            "line_items": line_items
        }
        
        LOG.info(f"Successfully parsed bill: {hospital}, Total: ₹{total_amount}, Subtotal: ₹{subtotal}, GST: ₹{gst}, Items: {len(line_items)}")
        return result
        
    except Exception as e:
        LOG.exception(f"Error in parse_bill: {e}")
        raise


if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    # Mock OCR result for testing
    mock_ocr = {
        "text": """Apollo Hospital
        Bill Date: 15/03/2024
        Invoice No: INV-2024-001234
        
        Description                Qty    Unit    Amount
        Consultation Fee           1      500     500
        Blood Test - CBC           1      800     800
        X-Ray Chest               1      1200    1200
        Room Rent (Per Day)       3      2000    6000
        Medicines                 1      1500    1500
        
        Total Amount: ₹10,000
        """,
        "words": ["Apollo", "Hospital", "Bill", "Date:", "15/03/2024"],
        "boxes": [],
        "confidences": [95, 95, 90, 85, 90],
        "avg_confidence": 91
    }
    
    result = parse_bill(mock_ocr)
    print(f"\nParsed Result:")
    print(f"Hospital: {result['hospital']}")
    print(f"Date: {result['bill_date']}")
    print(f"Invoice: {result['invoice_no']}")
    print(f"Total: ₹{result['total_amount']}")
    print(f"Line Items: {len(result['line_items'])}")
