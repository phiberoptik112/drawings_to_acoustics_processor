"""
OCR & Import Settings
--------------------
Manages user preferences for OCR engine selection, table detection,
and import validation settings.
"""

from __future__ import annotations

import json
import os
from typing import Optional
from dataclasses import dataclass, asdict
from enum import Enum


class OCREnginePreference(Enum):
    """User's preferred OCR engine"""
    PADDLE = "paddle"
    EASY = "easy"
    TESSERACT = "tesseract"
    AUTO = "auto"  # Try PaddleOCR, fallback to EasyOCR, then Tesseract


@dataclass
class OCRSettings:
    """OCR and import settings"""
    # OCR Engine
    preferred_engine: str = "auto"  # paddle, easy, tesseract, or auto
    
    # Table Detection
    enable_auto_detection: bool = True
    detection_confidence_threshold: float = 0.5
    show_confidence_scores: bool = True
    
    # Validation
    auto_fix_common_errors: bool = True
    highlight_missing_values: bool = True
    warn_on_duplicates: bool = True
    
    # Cloud OCR (Optional)
    enable_cloud_ocr: bool = False
    cloud_service: str = "google"  # google, aws, azure
    cloud_api_key: str = ""
    
    # Import Options
    create_backup_before_import: bool = True
    skip_duplicate_units: bool = True
    
    @classmethod
    def load(cls, settings_file: Optional[str] = None) -> OCRSettings:
        """Load settings from file"""
        if settings_file is None:
            settings_file = cls.get_default_settings_path()
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    data = json.load(f)
                return cls(**data)
            except Exception as e:
                print(f"Failed to load OCR settings: {e}")
                return cls()
        else:
            return cls()
    
    def save(self, settings_file: Optional[str] = None):
        """Save settings to file"""
        if settings_file is None:
            settings_file = self.get_default_settings_path()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        
        try:
            with open(settings_file, 'w') as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as e:
            print(f"Failed to save OCR settings: {e}")
    
    @staticmethod
    def get_default_settings_path() -> str:
        """Get default settings file path"""
        # Store in user's home directory
        home = os.path.expanduser("~")
        settings_dir = os.path.join(home, ".acoustics_processor")
        return os.path.join(settings_dir, "ocr_settings.json")


class OCRSettingsManager:
    """
    Singleton manager for OCR settings
    """
    _instance: Optional[OCRSettingsManager] = None
    
    def __init__(self):
        self.settings = OCRSettings.load()
    
    @classmethod
    def get_instance(cls) -> OCRSettingsManager:
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = OCRSettingsManager()
        return cls._instance
    
    def get_settings(self) -> OCRSettings:
        """Get current settings"""
        return self.settings
    
    def update_settings(self, **kwargs):
        """Update settings"""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.settings.save()
    
    def reset_to_defaults(self):
        """Reset to default settings"""
        self.settings = OCRSettings()
        self.settings.save()


def get_ocr_settings() -> OCRSettings:
    """Convenience function to get current OCR settings"""
    return OCRSettingsManager.get_instance().get_settings()


def update_ocr_settings(**kwargs):
    """Convenience function to update OCR settings"""
    OCRSettingsManager.get_instance().update_settings(**kwargs)
