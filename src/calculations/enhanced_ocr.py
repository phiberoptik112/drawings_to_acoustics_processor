"""
Enhanced OCR Engine
------------------
Multi-tier OCR system with PaddleOCR/EasyOCR and Tesseract fallback.
Provides better accuracy than Tesseract alone with confidence scoring.
"""

from __future__ import annotations

import os
import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


class OCREngine(Enum):
    """Available OCR engines"""
    PADDLE = "paddle"
    EASY = "easy"
    TESSERACT = "tesseract"


@dataclass
class OCRResult:
    """Result from OCR operation"""
    text: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    engine_used: OCREngine = OCREngine.TESSERACT
    
    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.8
    
    @property
    def is_medium_confidence(self) -> bool:
        return 0.5 <= self.confidence < 0.8
    
    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5


@dataclass
class TableOCRResult:
    """Result from table extraction"""
    rows: List[List[str]]
    confidences: List[List[float]]
    engine_used: OCREngine
    extraction_time: float
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across all cells"""
        if not self.confidences:
            return 0.0
        total = sum(sum(row) for row in self.confidences)
        count = sum(len(row) for row in self.confidences)
        return total / count if count > 0 else 0.0


class EnhancedOCR:
    """
    Enhanced OCR engine with multiple backends and fallback chain
    """
    
    def __init__(self, preferred_engine: OCREngine = OCREngine.PADDLE):
        self.preferred_engine = preferred_engine
        self.paddle_ocr = None
        self.easy_ocr = None
        self.tesseract_available = self._check_tesseract()
        
        # Try to initialize preferred engine
        if preferred_engine == OCREngine.PADDLE:
            self._init_paddle()
        elif preferred_engine == OCREngine.EASY:
            self._init_easy()
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available"""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
            return False
    
    def _init_paddle(self) -> bool:
        """Initialize PaddleOCR"""
        if self.paddle_ocr is not None:
            return True
        
        try:
            from paddleocr import PaddleOCR
            
            # Initialize with English language, no logging
            self.paddle_ocr = PaddleOCR(
                use_angle_cls=True,  # Enable angle classification
                lang='en',
                use_gpu=False,  # Use CPU by default (GPU auto-detected if available)
                show_log=False
            )
            logger.info("PaddleOCR initialized successfully")
            return True
        except ImportError:
            logger.warning("PaddleOCR not installed. Install with: pip install paddleocr")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            return False
    
    def _init_easy(self) -> bool:
        """Initialize EasyOCR"""
        if self.easy_ocr is not None:
            return True
        
        try:
            import easyocr
            
            # Initialize with English language
            self.easy_ocr = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR initialized successfully")
            return True
        except ImportError:
            logger.warning("EasyOCR not installed. Install with: pip install easyocr")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            return False
    
    def extract_text(self, image: np.ndarray, bbox: Optional[Tuple[int, int, int, int]] = None) -> OCRResult:
        """
        Extract text from image or image region with confidence scoring
        
        Args:
            image: Image as numpy array (BGR format)
            bbox: Optional bounding box (x, y, w, h) to crop before OCR
        
        Returns:
            OCRResult with text, confidence, and engine used
        """
        # Crop to bbox if provided
        if bbox:
            x, y, w, h = bbox
            image = image[y:y+h, x:x+w]
        
        # Try engines in order of preference
        engines_to_try = [self.preferred_engine]
        
        # Add fallbacks
        if self.preferred_engine != OCREngine.PADDLE and self.paddle_ocr is not None:
            engines_to_try.append(OCREngine.PADDLE)
        if self.preferred_engine != OCREngine.EASY and self.easy_ocr is not None:
            engines_to_try.append(OCREngine.EASY)
        if self.tesseract_available:
            engines_to_try.append(OCREngine.TESSERACT)
        
        last_error = None
        for engine in engines_to_try:
            try:
                if engine == OCREngine.PADDLE:
                    return self._extract_paddle(image)
                elif engine == OCREngine.EASY:
                    return self._extract_easy(image)
                elif engine == OCREngine.TESSERACT:
                    return self._extract_tesseract(image)
            except Exception as e:
                last_error = e
                logger.warning(f"{engine.value} OCR failed: {e}")
                continue
        
        # All engines failed
        logger.error(f"All OCR engines failed. Last error: {last_error}")
        return OCRResult(text="", confidence=0.0, bbox=bbox, engine_used=OCREngine.TESSERACT)
    
    def _extract_paddle(self, image: np.ndarray) -> OCRResult:
        """Extract text using PaddleOCR"""
        if self.paddle_ocr is None and not self._init_paddle():
            raise RuntimeError("PaddleOCR not available")
        
        # PaddleOCR expects RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        results = self.paddle_ocr.ocr(image_rgb, cls=True)
        
        if not results or not results[0]:
            return OCRResult(text="", confidence=0.0, engine_used=OCREngine.PADDLE)
        
        # Combine all detected text with confidence
        texts = []
        confidences = []
        
        for line in results[0]:
            if line:
                bbox_coords, (text, conf) = line
                texts.append(text)
                confidences.append(conf)
        
        combined_text = " ".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=combined_text,
            confidence=avg_confidence,
            engine_used=OCREngine.PADDLE
        )
    
    def _extract_easy(self, image: np.ndarray) -> OCRResult:
        """Extract text using EasyOCR"""
        if self.easy_ocr is None and not self._init_easy():
            raise RuntimeError("EasyOCR not available")
        
        # EasyOCR expects RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        results = self.easy_ocr.readtext(image_rgb)
        
        if not results:
            return OCRResult(text="", confidence=0.0, engine_used=OCREngine.EASY)
        
        # Combine all detected text with confidence
        texts = []
        confidences = []
        
        for bbox, text, conf in results:
            texts.append(text)
            confidences.append(conf)
        
        combined_text = " ".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=combined_text,
            confidence=avg_confidence,
            engine_used=OCREngine.EASY
        )
    
    def _extract_tesseract(self, image: np.ndarray) -> OCRResult:
        """Extract text using Tesseract"""
        import pytesseract
        from PIL import Image
        
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Preprocess for better results
        # 1. Resize if too small
        if gray.shape[0] < 50 or gray.shape[1] < 50:
            scale = 2
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # 2. Binarize with Otsu's method
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(binary)
        
        # Get text with confidence
        try:
            data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
            
            # Extract text and calculate average confidence
            texts = []
            confidences = []
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                
                if text and conf > 0:
                    texts.append(text)
                    confidences.append(conf / 100.0)  # Normalize to 0-1
            
            combined_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                engine_used=OCREngine.TESSERACT
            )
        except Exception as e:
            # Fallback to simple string extraction
            logger.warning(f"Tesseract data extraction failed, using simple string: {e}")
            text = pytesseract.image_to_string(pil_image).strip()
            return OCRResult(
                text=text,
                confidence=0.5,  # Unknown confidence
                engine_used=OCREngine.TESSERACT
            )
    
    def extract_table(self, image: np.ndarray, use_existing_grid: bool = True) -> TableOCRResult:
        """
        Extract table data from image
        
        Args:
            image: Image as numpy array (BGR format)
            use_existing_grid: If True, use existing grid detection from image_table_to_csv
        
        Returns:
            TableOCRResult with rows, confidences, and metadata
        """
        import time
        start_time = time.perf_counter()
        
        if use_existing_grid:
            # Use existing grid detection logic from image_table_to_csv
            from .image_table_to_csv import extract_table
            
            # Extract table structure
            rows = extract_table(image, enhanced=True)
            
            # Re-run OCR on each cell with confidence scoring
            # For now, assume medium confidence for grid-based extraction
            confidences = [[0.75 for _ in row] for row in rows]
            
            engine_used = self.preferred_engine
        else:
            # Direct OCR without grid detection
            # This is less accurate for tables but works on borderless tables
            result = self.extract_text(image)
            
            # Split text into rows (naive approach)
            lines = result.text.split('\n')
            rows = [line.split() for line in lines if line.strip()]
            confidences = [[result.confidence for _ in row] for row in rows]
            engine_used = result.engine_used
        
        elapsed = time.perf_counter() - start_time
        
        return TableOCRResult(
            rows=rows,
            confidences=confidences,
            engine_used=engine_used,
            extraction_time=elapsed
        )
    
    def get_available_engines(self) -> List[OCREngine]:
        """Get list of available OCR engines"""
        engines = []
        
        if self.paddle_ocr is not None or self._init_paddle():
            engines.append(OCREngine.PADDLE)
        
        if self.easy_ocr is not None or self._init_easy():
            engines.append(OCREngine.EASY)
        
        if self.tesseract_available:
            engines.append(OCREngine.TESSERACT)
        
        return engines


# Global instance for convenience
_global_ocr_instance: Optional[EnhancedOCR] = None


def get_ocr_engine(preferred: OCREngine = OCREngine.PADDLE) -> EnhancedOCR:
    """Get or create global OCR engine instance"""
    global _global_ocr_instance
    
    if _global_ocr_instance is None:
        _global_ocr_instance = EnhancedOCR(preferred_engine=preferred)
    
    return _global_ocr_instance


def extract_text_with_confidence(image: np.ndarray, engine: OCREngine = OCREngine.PADDLE) -> OCRResult:
    """
    Convenience function to extract text with confidence
    
    Args:
        image: Image as numpy array (BGR)
        engine: Preferred OCR engine
    
    Returns:
        OCRResult with text and confidence
    """
    ocr = get_ocr_engine(engine)
    return ocr.extract_text(image)


def extract_table_with_confidence(image: np.ndarray, engine: OCREngine = OCREngine.PADDLE) -> TableOCRResult:
    """
    Convenience function to extract table with confidence scores
    
    Args:
        image: Image as numpy array (BGR)
        engine: Preferred OCR engine
    
    Returns:
        TableOCRResult with rows and confidences
    """
    ocr = get_ocr_engine(engine)
    return ocr.extract_table(image)
