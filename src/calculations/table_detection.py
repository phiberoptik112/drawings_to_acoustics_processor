"""
Table Detection using Table Transformer
---------------------------------------
Uses Microsoft's Table Transformer model for detecting table regions
in documents with high accuracy.
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class DetectedTable:
    """A detected table region"""
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    label: str = "Table"
    
    @property
    def area(self) -> int:
        return self.bbox[2] * self.bbox[3]
    
    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.75
    
    @property
    def center(self) -> Tuple[int, int]:
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)


class TableDetector:
    """
    Table detection using Table Transformer model from Hugging Face
    """
    
    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.feature_extractor = None
        self.device = "cpu"  # Will auto-detect GPU if available
        
    def _init_model(self) -> bool:
        """Initialize the Table Transformer model"""
        if self.model is not None:
            return True
        
        try:
            from transformers import AutoModelForObjectDetection, AutoImageProcessor
            import torch
            
            # Check for GPU
            if torch.cuda.is_available():
                self.device = "cuda"
                logger.info("GPU detected, using CUDA for table detection")
            else:
                logger.info("Using CPU for table detection")
            
            # Load pre-trained Table Transformer model
            model_name = "microsoft/table-transformer-detection"
            
            logger.info(f"Loading Table Transformer model: {model_name}")
            self.feature_extractor = AutoImageProcessor.from_pretrained(model_name)
            self.model = AutoModelForObjectDetection.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("Table Transformer model loaded successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Required packages not installed: {e}")
            logger.error("Install with: pip install transformers torch torchvision timm")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Table Transformer: {e}")
            return False
    
    def detect_tables(self, image: np.ndarray, min_confidence: Optional[float] = None) -> List[DetectedTable]:
        """
        Detect tables in an image
        
        Args:
            image: Image as numpy array (BGR format from cv2)
            min_confidence: Minimum confidence threshold (overrides default)
        
        Returns:
            List of DetectedTable objects with bounding boxes and confidence scores
        """
        if not self._init_model():
            logger.warning("Table detection model not available, falling back to mock detection")
            return self._fallback_detection(image)
        
        try:
            import torch
            
            # Convert BGR to RGB
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            
            # Convert to PIL Image
            pil_image = Image.fromarray(image_rgb)
            
            # Prepare image for model
            inputs = self.feature_extractor(images=pil_image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Run detection
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Post-process results
            threshold = min_confidence if min_confidence is not None else self.confidence_threshold
            target_sizes = torch.tensor([pil_image.size[::-1]])  # height, width
            results = self.feature_extractor.post_process_object_detection(
                outputs,
                threshold=threshold,
                target_sizes=target_sizes
            )[0]
            
            # Extract detected tables
            detected_tables = []
            
            for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                score_value = score.item()
                box_coords = box.tolist()
                
                # Convert from [x1, y1, x2, y2] to [x, y, width, height]
                x1, y1, x2, y2 = box_coords
                bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                
                detected_tables.append(DetectedTable(
                    bbox=bbox,
                    confidence=score_value,
                    label=f"Table {len(detected_tables) + 1}"
                ))
            
            # Sort by confidence
            detected_tables.sort(key=lambda t: t.confidence, reverse=True)
            
            logger.info(f"Detected {len(detected_tables)} tables with confidence >= {threshold:.2f}")
            return detected_tables
            
        except Exception as e:
            logger.error(f"Table detection failed: {e}")
            return []
    
    def _fallback_detection(self, image: np.ndarray) -> List[DetectedTable]:
        """
        Fallback table detection using simple heuristics
        Used when Table Transformer is not available
        """
        logger.info("Using fallback table detection (edge-based heuristics)")
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter for large rectangular regions
        detected_tables = []
        image_area = gray.shape[0] * gray.shape[1]
        min_area = image_area * 0.05  # At least 5% of image
        
        for i, contour in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            # Filter by size and aspect ratio
            if area >= min_area and 0.3 <= w / h <= 3.0:
                # Estimate confidence based on rectangularity
                rect_area = w * h
                contour_area = cv2.contourArea(contour)
                rectangularity = contour_area / rect_area if rect_area > 0 else 0
                confidence = min(0.6, rectangularity)  # Cap at 0.6 for fallback
                
                detected_tables.append(DetectedTable(
                    bbox=(x, y, w, h),
                    confidence=confidence,
                    label=f"Region {i + 1}"
                ))
        
        # Sort by size (larger tables more likely)
        detected_tables.sort(key=lambda t: t.area, reverse=True)
        
        # Return top 3 candidates
        return detected_tables[:3]
    
    def detect_table_structure(self, image: np.ndarray, table_bbox: Tuple[int, int, int, int]) -> dict:
        """
        Detect the internal structure of a table (rows and columns)
        
        Args:
            image: Full image as numpy array (BGR)
            table_bbox: Bounding box of table (x, y, width, height)
        
        Returns:
            Dictionary with detected structure information
        """
        # Crop to table region
        x, y, w, h = table_bbox
        table_image = image[y:y+h, x:x+w]
        
        # This would use Table Transformer structure recognition model
        # For now, return placeholder structure
        logger.info("Table structure detection not yet implemented")
        
        return {
            "rows": [],
            "columns": [],
            "cells": [],
            "confidence": 0.0
        }
    
    def visualize_detections(self, image: np.ndarray, detections: List[DetectedTable]) -> np.ndarray:
        """
        Draw detected tables on image for visualization
        
        Args:
            image: Image as numpy array (BGR)
            detections: List of detected tables
        
        Returns:
            Image with drawn bounding boxes
        """
        vis_image = image.copy()
        
        for detection in detections:
            x, y, w, h = detection.bbox
            
            # Color code by confidence
            if detection.is_high_confidence:
                color = (0, 255, 0)  # Green for high confidence
            else:
                color = (0, 165, 255)  # Orange for lower confidence
            
            # Draw rectangle
            cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 2)
            
            # Draw label with confidence
            label_text = f"{detection.label} ({detection.confidence:.0%})"
            label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            # Draw label background
            cv2.rectangle(
                vis_image,
                (x, y - label_size[1] - 10),
                (x + label_size[0], y),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                vis_image,
                label_text,
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
        
        return vis_image


# Global instance for convenience
_global_detector: Optional[TableDetector] = None


def get_table_detector(confidence_threshold: float = 0.5) -> TableDetector:
    """Get or create global table detector instance"""
    global _global_detector
    
    if _global_detector is None:
        _global_detector = TableDetector(confidence_threshold=confidence_threshold)
    
    return _global_detector


def detect_tables_in_image(image: np.ndarray, min_confidence: float = 0.5) -> List[DetectedTable]:
    """
    Convenience function to detect tables in an image
    
    Args:
        image: Image as numpy array (BGR from cv2)
        min_confidence: Minimum confidence threshold
    
    Returns:
        List of DetectedTable objects
    """
    detector = get_table_detector(confidence_threshold=min_confidence)
    return detector.detect_tables(image, min_confidence=min_confidence)


def visualize_table_detection(image: np.ndarray, detections: List[DetectedTable]) -> np.ndarray:
    """
    Convenience function to visualize table detections
    
    Args:
        image: Image as numpy array (BGR)
        detections: List of detected tables
    
    Returns:
        Image with drawn bounding boxes
    """
    detector = get_table_detector()
    return detector.visualize_detections(image, detections)
