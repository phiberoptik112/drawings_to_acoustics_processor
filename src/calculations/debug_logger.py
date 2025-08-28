"""
Debug logging framework for HVAC calculations
Centralizes and standardizes debug output across the calculation system
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


class HVACDebugLogger:
    """Centralized debug logger for HVAC calculation system"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._setup_logger()
            HVACDebugLogger._initialized = True
    
    def _setup_logger(self):
        """Initialize the logging configuration"""
        # Check environment variable for debug level
        env_val = str(os.environ.get("HVAC_DEBUG_EXPORT", "")).strip().lower()
        self.debug_enabled = env_val in {"1", "true", "yes", "on"}
        
        # Set up logging level
        debug_level = os.environ.get("HVAC_DEBUG_LEVEL", "INFO").upper()
        
        # Create logger
        self.logger = logging.getLogger('hvac_debug')
        self.logger.setLevel(getattr(logging, debug_level, logging.INFO))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Only add handlers if debug is enabled
        if self.debug_enabled:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            
            # Format with timestamp and component
            formatter = logging.Formatter(
                '%(asctime)s [HVAC-%(levelname)s] %(component)s: %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # File handler if requested
            if os.environ.get("HVAC_DEBUG_FILE"):
                file_handler = logging.FileHandler('hvac_debug.log')
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
    
    def debug(self, component: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log debug message with component context"""
        if not self.debug_enabled:
            return
            
        # Format message with data if provided
        if data:
            formatted_data = self._format_debug_data(data)
            full_message = f"{message} {formatted_data}"
        else:
            full_message = message
            
        self.logger.debug(full_message, extra={'component': component})
    
    def info(self, component: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log info message with component context"""
        if not self.debug_enabled:
            return
            
        if data:
            formatted_data = self._format_debug_data(data)
            full_message = f"{message} {formatted_data}"
        else:
            full_message = message
            
        self.logger.info(full_message, extra={'component': component})
    
    def warning(self, component: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log warning message with component context"""
        if not self.debug_enabled:
            return
            
        if data:
            formatted_data = self._format_debug_data(data)
            full_message = f"{message} {formatted_data}"
        else:
            full_message = message
            
        self.logger.warning(full_message, extra={'component': component})
    
    def error(self, component: str, message: str, error: Optional[Exception] = None, data: Optional[Dict[str, Any]] = None):
        """Log error message with component context"""
        if not self.debug_enabled:
            return
            
        full_message = message
        if error:
            full_message += f" Error: {str(error)}"
        if data:
            formatted_data = self._format_debug_data(data)
            full_message += f" {formatted_data}"
            
        self.logger.error(full_message, extra={'component': component})
    
    def _format_debug_data(self, data: Dict[str, Any]) -> str:
        """Format debug data for logging"""
        try:
            # Handle common HVAC data types
            formatted = {}
            for key, value in data.items():
                if key in ['spectrum', 'octave_bands', 'attenuation_spectrum', 'generated_spectrum']:
                    # Format spectrum data
                    if isinstance(value, list) and len(value) == 8:
                        formatted[key] = [f"{float(v):.1f}" for v in value]
                    else:
                        formatted[key] = value
                elif key.endswith('_dba') or key.endswith('_level'):
                    # Format dBA values
                    if isinstance(value, (int, float)):
                        formatted[key] = f"{float(value):.1f}dBA"
                    else:
                        formatted[key] = value
                elif key in ['nc_rating', 'id', 'order']:
                    # Format integers
                    formatted[key] = int(value) if value is not None else None
                else:
                    formatted[key] = value
            
            return json.dumps(formatted, separators=(',', ':'))
        except Exception:
            # Fallback to string representation
            return str(data)
    
    def log_calculation_start(self, component: str, calculation_type: str, path_id: Optional[int] = None):
        """Log the start of a calculation"""
        data = {'calculation_type': calculation_type}
        if path_id:
            data['path_id'] = path_id
        self.info(component, "Starting calculation", data)
    
    def log_calculation_end(self, component: str, calculation_type: str, success: bool, result_summary: Optional[Dict] = None):
        """Log the end of a calculation"""
        status = "completed" if success else "failed"
        data = {'calculation_type': calculation_type, 'status': status}
        if result_summary:
            data.update(result_summary)
        self.info(component, "Calculation finished", data)
    
    def log_element_processing(self, component: str, element_type: str, element_id: str, 
                             input_spectrum: Optional[List[float]] = None, 
                             output_spectrum: Optional[List[float]] = None,
                             attenuation_dba: Optional[float] = None):
        """Log element processing details"""
        data = {
            'element_type': element_type,
            'element_id': element_id
        }
        if input_spectrum:
            data['input_spectrum'] = input_spectrum
        if output_spectrum:
            data['output_spectrum'] = output_spectrum
        if attenuation_dba is not None:
            data['attenuation_dba'] = attenuation_dba
            
        self.debug(component, "Processing element", data)
    
    def log_validation_result(self, component: str, is_valid: bool, errors: List[str], warnings: List[str]):
        """Log validation results"""
        data = {
            'is_valid': is_valid,
            'error_count': len(errors),
            'warning_count': len(warnings)
        }
        if errors:
            data['errors'] = errors
        if warnings:
            data['warnings'] = warnings
            
        if is_valid:
            self.info(component, "Validation passed", data)
        else:
            self.warning(component, "Validation failed", data)


# Global logger instance
debug_logger = HVACDebugLogger()