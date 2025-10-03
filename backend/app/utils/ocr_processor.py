# utils/ocr_processor.py
import os
from PIL import Image
import io
from typing import Tuple, Optional

def ocr_from_image_bytes(image_bytes: bytes, tesseract_cmd: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Try to extract text from image bytes using pytesseract if installed.
    Falls back to returning (None, reason) if pytesseract not available or OCR fails.
    Returns: (text_or_none, error_or_none)
    """
    try:
        import pytesseract  # type: ignore
    except Exception:
        return None, "pytesseract not installed"

    if tesseract_cmd:
        os.environ['TESSERACT_CMD'] = tesseract_cmd

    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        return text, None
    except Exception as e:
        return None, str(e)
