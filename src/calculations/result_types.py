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


@dataclass
class SurfaceData:
    """Data for a single surface in RT60 calculation"""
    surface_type: str
    area: float
    material_key: str
    material_name: str
    absorption_coeff: float
    absorption: float
    is_door_window: bool = False


@dataclass
class RT60Result:
    """Result of RT60 calculation"""
    rt60: float
    method: str
    volume: float
    surfaces: List['SurfaceData']
    total_area: float
    total_absorption: float
    avg_absorption_coeff: float
    rt60_by_frequency: Optional[dict] = None
    is_valid: bool = True
    error_message: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    @classmethod
    def error(cls, error_message: str, method: str = 'sabine') -> 'RT60Result':
        """Create an error result"""
        return cls(
            rt60=float('inf'),
            method=method,
            volume=0.0,
            surfaces=[],
            total_area=0.0,
            total_absorption=0.0,
            avg_absorption_coeff=0.0,
            is_valid=False,
            error_message=error_message
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility"""
        result = {
            'rt60': self.rt60 if self.is_valid else 999.9,
            'method': self.method,
            'volume': self.volume,
            'surfaces': [
                {
                    'type': s.surface_type,
                    'area': s.area,
                    'material_key': s.material_key,
                    'material_name': s.material_name,
                    'absorption_coeff': s.absorption_coeff,
                    'absorption': s.absorption,
                    'is_door_window': s.is_door_window
                }
                for s in self.surfaces
            ],
            'total_area': self.total_area,
            'total_absorption': self.total_absorption,
            'avg_absorption_coeff': self.avg_absorption_coeff
        }
        if self.rt60_by_frequency:
            result['rt60_by_frequency'] = self.rt60_by_frequency
        if self.error_message:
            result['error'] = self.error_message
        return result


@dataclass
class NCAnalysisData:
    """Result data for NC rating analysis"""
    nc_rating: int
    overall_dba: float
    octave_band_levels: dict  # freq -> level
    meets_target: bool
    target_nc: Optional[int] = None
    margin: Optional[float] = None
    dominant_frequency: Optional[int] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []