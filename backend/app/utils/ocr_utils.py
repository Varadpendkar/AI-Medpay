"""
OCR Utilities for Bill Scanner
Handles image preprocessing and text extraction using Tesseract OCR
Supports PDF, HEIC, and standard image formats
"""
import os
import logging
import cv2
import numpy as np
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from pathlib import Path
from typing import Dict, List, Tuple

# HEIC support - optional imports with fallbacks
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    _HAS_PILLOW_HEIF = True
except Exception:
    _HAS_PILLOW_HEIF = False

try:
    import pyheif
    _HAS_PYHEIF = True
except Exception:
    _HAS_PYHEIF = False

LOG = logging.getLogger(__name__)

# Configure Tesseract path (adjust if needed)
# pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'  # Mac/Linux
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows


def _convert_heic_with_pyheif(src_path: str, dst_path: str) -> str:
    """
    Convert HEIC to JPEG using pyheif library
    
    Args:
        src_path: Path to HEIC file
        dst_path: Path to save JPEG
    
    Returns:
        Path to converted JPEG file
    """
    heif_file = pyheif.read(src_path)
    image = Image.frombytes(
        heif_file.mode, 
        heif_file.size, 
        heif_file.data,
        "raw",
        heif_file.mode,
        heif_file.stride,
    )
    image.save(dst_path, format="JPEG", quality=90)
    LOG.info(f"Converted HEIC to JPEG: {dst_path}")
    return dst_path


def _normalize_pil_image(img: Image.Image) -> Image.Image:
    """
    Normalize PIL image: convert to RGB, resize if too large
    
    Args:
        img: PIL Image
    
    Returns:
        Normalized PIL Image
    """
    # Convert to RGB
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    # Resize if too large (for memory efficiency)
    max_dim = 3500
    if max(img.size) > max_dim:
        scale = max_dim / max(img.size)
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size, Image.LANCZOS)
        LOG.info(f"Resized image from {img.size} to {new_size}")
    
    return img


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Preprocess image for better OCR accuracy
    
    Args:
        image: Input image as numpy array (BGR format from cv2)
    
    Returns:
        Preprocessed image ready for OCR
    """
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Resize if too small (upscale to at least 1000px width)
        height, width = gray.shape
        if width < 1000:
            scale = 1000 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            LOG.info(f"Upscaled image from {width}x{height} to {new_width}x{new_height}")
        
        # Denoise
        denoised = cv2.medianBlur(gray, 3)
        
        # Adaptive thresholding for better binarization
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Optional: deskew if image is rotated
        # (skipped for now - can add angle detection with cv2.minAreaRect if needed)
        
        return binary
        
    except Exception as e:
        LOG.error(f"Error in image preprocessing: {e}")
        return image


def pdf_to_images(pdf_path: str) -> List[np.ndarray]:
    """
    Convert PDF to list of images (one per page)
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        List of images as numpy arrays
    """
    try:
        # Convert PDF to PIL Images
        pil_images = convert_from_path(pdf_path, dpi=300)
        
        # Convert PIL to numpy arrays (OpenCV format)
        images = []
        for pil_img in pil_images:
            # Convert PIL RGB to OpenCV BGR
            img_array = np.array(pil_img)
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            images.append(img_bgr)
        
        LOG.info(f"Converted PDF to {len(images)} images")
        return images
        
    except Exception as e:
        LOG.error(f"Error converting PDF to images: {e}")
        raise


def preprocess_and_ocr(file_path: str) -> Dict:
    """
    Main OCR pipeline: load file (PDF/HEIC/images), preprocess, extract text and metadata
    
    Supports:
        - PDF files (converted to images)
        - HEIC/HEIF files (converted to JPEG)
        - Standard image formats (PNG, JPG, JPEG, TIFF, BMP)
    
    Args:
        file_path: Path to image or PDF file
    
    Returns:
        Dictionary containing:
            - text: Full extracted text
            - words: List of individual words
            - boxes: Bounding boxes for each word (x, y, w, h)
            - confidences: OCR confidence scores (0-100) for each word
            - avg_confidence: Average confidence across all words
    """
    try:
        file_path = str(file_path)
        ext = Path(file_path).suffix.lower()
        work_dir = os.path.dirname(file_path)
        temp_files = []  # Track temporary files for cleanup
        
        # Handle different file types
        if ext == '.pdf':
            # PDF: convert to images
            LOG.info("Processing PDF file")
            images = pdf_to_images(file_path)
            # Process first page (can extend to multi-page)
            image = images[0]
            
        elif ext in ['.heic', '.heif']:
            # HEIC: convert to standard format
            LOG.info("Processing HEIC/HEIF file")
            try:
                # Try native Pillow open (with pillow_heif)
                pil_img = Image.open(file_path)
                pil_img = _normalize_pil_image(pil_img)
                
                # Save as temporary PNG for OpenCV processing
                temp_png = os.path.join(work_dir, Path(file_path).stem + "_conv.png")
                pil_img.save(temp_png, "PNG")
                temp_files.append(temp_png)
                
                # Load with OpenCV
                image = cv2.imread(temp_png)
                if image is None:
                    raise ValueError(f"Failed to load converted image from {temp_png}")
                    
            except Exception as e:
                LOG.warning(f"Pillow couldn't open HEIC natively: {e}")
                # Fallback to pyheif conversion
                if _HAS_PYHEIF:
                    temp_jpeg = os.path.join(work_dir, Path(file_path).stem + "_conv.jpg")
                    _convert_heic_with_pyheif(file_path, temp_jpeg)
                    temp_files.append(temp_jpeg)
                    
                    image = cv2.imread(temp_jpeg)
                    if image is None:
                        raise ValueError(f"Failed to load converted image from {temp_jpeg}")
                else:
                    raise ValueError(
                        f"HEIC file detected but no conversion support available. "
                        f"Install pillow-heif or pyheif. Has pillow-heif: {_HAS_PILLOW_HEIF}, "
                        f"Has pyheif: {_HAS_PYHEIF}"
                    )
        
        else:
            # Standard image formats (PNG, JPG, JPEG, TIFF, BMP, etc.)
            LOG.info(f"Processing image file: {ext}")
            image = cv2.imread(file_path)
            if image is None:
                # Try with PIL as fallback
                try:
                    pil_img = Image.open(file_path)
                    pil_img = _normalize_pil_image(pil_img)
                    
                    # Convert to OpenCV format
                    img_array = np.array(pil_img)
                    if len(img_array.shape) == 3:
                        image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                    else:
                        image = img_array
                        
                    if image is None:
                        raise ValueError(f"Failed to load image from {file_path}")
                except Exception as e:
                    raise ValueError(f"Failed to load image from {file_path}: {e}")
        
        LOG.info(f"Loaded image with shape: {image.shape}")
        
        # Preprocess
        processed = preprocess_image(image)
        
        # Run Tesseract OCR with detailed output
        ocr_data = pytesseract.image_to_data(
            processed, 
            output_type=pytesseract.Output.DICT,
            lang='eng',
            config='--psm 6'  # Assume uniform block of text
        )
        
        # Extract full text
        full_text = pytesseract.image_to_string(processed, lang='eng')
        
        # Filter out low-confidence results and empty words
        words = []
        boxes = []
        confidences = []
        
        for i in range(len(ocr_data['text'])):
            word = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])
            
            if word and conf > 0:  # Only keep non-empty words with confidence
                words.append(word)
                confidences.append(conf)
                boxes.append({
                    'x': ocr_data['left'][i],
                    'y': ocr_data['top'][i],
                    'w': ocr_data['width'][i],
                    'h': ocr_data['height'][i]
                })
        
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        
        LOG.info(f"OCR extracted {len(words)} words with avg confidence {avg_conf:.1f}%")
        
        # Cleanup temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    LOG.debug(f"Removed temporary file: {temp_file}")
            except Exception as e:
                LOG.warning(f"Failed to remove temporary file {temp_file}: {e}")
        
        return {
            "text": full_text,
            "words": words,
            "boxes": boxes,
            "confidences": confidences,
            "avg_confidence": avg_conf
        }
        
    except Exception as e:
        LOG.exception(f"Error in OCR processing: {e}")
        raise


def extract_text_regions(image: np.ndarray, regions: List[Tuple[int, int, int, int]]) -> List[str]:
    """
    Extract text from specific regions of an image
    
    Args:
        image: Input image
        regions: List of (x, y, width, height) tuples
    
    Returns:
        List of extracted text strings
    """
    texts = []
    for x, y, w, h in regions:
        roi = image[y:y+h, x:x+w]
        text = pytesseract.image_to_string(roi, lang='eng')
        texts.append(text.strip())
    return texts


if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    test_file = "test_bill.jpg"  # Replace with actual test file
    if os.path.exists(test_file):
        result = preprocess_and_ocr(test_file)
        print(f"Extracted text preview:\n{result['text'][:500]}")
        print(f"\nTotal words: {len(result['words'])}")
        print(f"Average confidence: {result['avg_confidence']:.1f}%")
