"""
Standardized result types for HVAC calculations
Ensures consistent return patterns across the calculation system
"""

from typing import Generic, TypeVar, Optional, List, Union, Any
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')


class ResultStatus(Enum):
    """Enumeration of possible result statuses"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class CalculationResult(Generic[T]):
    """
    Standardized result wrapper for HVAC calculation operations
    
    Provides consistent return types across all calculation methods
    """
    status: ResultStatus
    data: Optional[T] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_success(self) -> bool:
        """Check if the operation was successful"""
        return self.status == ResultStatus.SUCCESS
    
    @property
    def is_error(self) -> bool:
        """Check if the operation failed"""
        return self.status == ResultStatus.ERROR
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings"""
        return len(self.warnings) > 0
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        self.warnings.append(warning)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value"""
        self.metadata[key] = value
    
    @classmethod
    def success(cls, data: T, warnings: List[str] = None, metadata: dict = None) -> 'CalculationResult[T]':
        """Create a successful result"""
        return cls(
            status=ResultStatus.SUCCESS,
            data=data,
            warnings=warnings or [],
            metadata=metadata or {}
        )
    
    @classmethod
    def error(cls, error_message: str, data: Optional[T] = None, metadata: dict = None) -> 'CalculationResult[T]':
        """Create an error result"""
        return cls(
            status=ResultStatus.ERROR,
            data=data,
            error_message=error_message,
            metadata=metadata or {}
        )
    
    @classmethod
    def validation_failed(cls, error_message: str, warnings: List[str] = None, metadata: dict = None) -> 'CalculationResult[T]':
        """Create a validation failed result"""
        return cls(
            status=ResultStatus.VALIDATION_FAILED,
            error_message=error_message,
            warnings=warnings or [],
            metadata=metadata or {}
        )


@dataclass
class PathCreationResult:
    """Result of HVAC path creation operation"""
    path_id: Optional[int] = None
    path_name: Optional[str] = None
    component_count: int = 0
    segment_count: int = 0
    created_successfully: bool = False


@dataclass
class ValidationResult:
    """Result of validation operations"""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    validation_details: dict = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.validation_details is None:
            self.validation_details = {}
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)


@dataclass
class OperationResult:
    """Simple success/failure result for basic operations"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
    
    @classmethod
    def success_result(cls, message: str = None, data: dict = None) -> 'OperationResult':
        """Create a successful operation result"""
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_result(cls, message: str, data: dict = None) -> 'OperationResult':
        """Create an error operation result"""
        return cls(success=False, message=message, data=data)