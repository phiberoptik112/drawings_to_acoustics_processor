"""
HVAC Validation Framework - Unified validation for all HVAC calculations
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
import os

if TYPE_CHECKING:
    from models.hvac import HVACPath, HVACSegment


@dataclass
class ValidationResult:
    """Result of a validation operation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.info is None:
            self.info = []
    
    def add_error(self, message: str):
        """Add an error message"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)
    
    def add_info(self, message: str):
        """Add an info message"""
        self.info.append(message)
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)
        if not other.is_valid:
            self.is_valid = False
    
    def has_messages(self) -> bool:
        """Check if there are any messages"""
        return bool(self.errors or self.warnings or self.info)


class HVACValidationFramework:
    """Unified validation system for all HVAC calculations"""
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self.debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
    
    def validate_path(self, path: 'HVACPath') -> ValidationResult:
        """Comprehensive path validation"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])
        
        try:
            # Basic path validation
            if not path:
                result.add_error("Path object is None")
                return result
            
            if not hasattr(path, 'name') or not path.name:
                result.add_error("Path must have a name")
            
            if not hasattr(path, 'project_id') or path.project_id != self.project_id:
                result.add_error("Path project ID mismatch")
            
            # Validate segments
            if hasattr(path, 'segments'):
                segments = path.segments
                if not segments:
                    result.add_warning("Path has no segments")
                else:
                    for i, segment in enumerate(segments):
                        segment_result = self.validate_segment(segment)
                        if not segment_result.is_valid:
                            result.add_error(f"Segment {i+1} validation failed")
                        result.merge(segment_result)
                    
                    # Check segment connectivity
                    connectivity_result = self._validate_segment_connectivity(segments)
                    result.merge(connectivity_result)
            
            # Validate mechanical unit connection
            if hasattr(path, 'primary_source_id') and path.primary_source_id:
                mech_result = self.validate_mechanical_unit_connection(path)
                result.merge(mech_result)
            
            if self.debug_enabled:
                print(f"DEBUG: Path validation - Valid: {result.is_valid}, Errors: {len(result.errors)}, Warnings: {len(result.warnings)}")
            
        except Exception as e:
            result.add_error(f"Path validation failed: {e}")
            if self.debug_enabled:
                print(f"DEBUG: Path validation exception: {e}")
        
        return result
    
    def validate_segment(self, segment: 'HVACSegment') -> ValidationResult:
        """Segment-specific validation"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])
        
        try:
            if not segment:
                result.add_error("Segment object is None")
                return result
            
            # Validate segment connections
            from_comp_id = getattr(segment, 'from_component_id', None)
            to_comp_id = getattr(segment, 'to_component_id', None)
            
            if not from_comp_id and not to_comp_id:
                result.add_error("Segment must have at least one connection")
            
            # Validate segment properties
            length = getattr(segment, 'length', None)
            if length is not None:
                if length <= 0:
                    result.add_warning("Segment length should be positive")
                elif length > 1000:  # 1000 feet seems excessive
                    result.add_warning(f"Segment length ({length:.1f} ft) is unusually large")
            
            # Validate duct dimensions
            duct_width = getattr(segment, 'duct_width', None)
            duct_height = getattr(segment, 'duct_height', None)
            duct_shape = getattr(segment, 'duct_shape', 'rectangular')
            
            if duct_shape == 'rectangular':
                if duct_width and (duct_width < 4 or duct_width > 60):
                    result.add_warning(f"Duct width ({duct_width}) outside typical range (4-60 inches)")
                if duct_height and (duct_height < 4 or duct_height > 60):
                    result.add_warning(f"Duct height ({duct_height}) outside typical range (4-60 inches)")
            elif duct_shape == 'circular':
                # For circular ducts, width is diameter
                if duct_width and (duct_width < 6 or duct_width > 60):
                    result.add_warning(f"Duct diameter ({duct_width}) outside typical range (6-60 inches)")
            
            # Validate segment order
            segment_order = getattr(segment, 'segment_order', None)
            if segment_order is not None and segment_order <= 0:
                result.add_error("Segment order must be positive")
            
        except Exception as e:
            result.add_error(f"Segment validation failed: {e}")
            if self.debug_enabled:
                print(f"DEBUG: Segment validation exception: {e}")
        
        return result
    
    def validate_mechanical_unit_connection(self, path: 'HVACPath') -> ValidationResult:
        """Validate mechanical unit integration"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])
        
        try:
            from models.database import get_hvac_session
            from models.mechanical import MechanicalUnit
            
            with get_hvac_session() as session:
                unit = session.query(MechanicalUnit).filter(
                    MechanicalUnit.id == path.primary_source_id,
                    MechanicalUnit.project_id == self.project_id
                ).first()
                
                if not unit:
                    result.add_error(f"Mechanical unit with ID {path.primary_source_id} not found")
                    return result
                
                # Validate unit properties
                if not unit.name:
                    result.add_warning("Mechanical unit has no name")
                
                if not unit.unit_type:
                    result.add_warning("Mechanical unit has no type specified")
                
                # Check airflow compatibility
                airflow = getattr(unit, 'airflow_cfm', None)
                if airflow:
                    if airflow < 100:
                        result.add_warning(f"Unit airflow ({airflow} CFM) seems low")
                    elif airflow > 50000:
                        result.add_warning(f"Unit airflow ({airflow} CFM) seems very high")
                    
                    result.add_info(f"Unit airflow: {airflow} CFM")
                else:
                    result.add_warning("No airflow data for mechanical unit")
                
                result.add_info(f"Connected to mechanical unit: {unit.name} ({unit.unit_type or 'unknown type'})")
                
        except Exception as e:
            result.add_error(f"Mechanical unit validation failed: {e}")
            if self.debug_enabled:
                print(f"DEBUG: Mechanical unit validation exception: {e}")
        
        return result
    
    def _validate_segment_connectivity(self, segments: List['HVACSegment']) -> ValidationResult:
        """Validate that segments form a connected path"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])
        
        try:
            if len(segments) <= 1:
                return result  # Single segment is trivially connected
            
            # Build connectivity map
            connections = {}
            component_ids = set()
            
            for segment in segments:
                from_id = getattr(segment, 'from_component_id', None)
                to_id = getattr(segment, 'to_component_id', None)
                
                if from_id:
                    component_ids.add(from_id)
                    if from_id not in connections:
                        connections[from_id] = []
                    if to_id:
                        connections[from_id].append(to_id)
                
                if to_id:
                    component_ids.add(to_id)
                    if to_id not in connections:
                        connections[to_id] = []
            
            # Check for disconnected segments
            if len(component_ids) > len(segments) + 1:
                result.add_warning("Path may have disconnected segments")
            
            # Find source and sink
            sources = []  # Components with no incoming connections
            sinks = []    # Components with no outgoing connections
            
            for comp_id in component_ids:
                has_incoming = any(comp_id in connections.get(other_id, []) for other_id in component_ids)
                has_outgoing = bool(connections.get(comp_id))
                
                if not has_incoming:
                    sources.append(comp_id)
                if not has_outgoing:
                    sinks.append(comp_id)
            
            if len(sources) == 0:
                result.add_warning("No clear source component found (circular path?)")
            elif len(sources) > 1:
                result.add_warning(f"Multiple source components found: {len(sources)}")
            
            if len(sinks) == 0:
                result.add_warning("No clear terminal component found (circular path?)")
            elif len(sinks) > 1:
                result.add_info(f"Multiple terminal components found: {len(sinks)}")
            
            result.add_info(f"Path connectivity: {len(component_ids)} components, {len(segments)} segments")
            
        except Exception as e:
            result.add_error(f"Connectivity validation failed: {e}")
            if self.debug_enabled:
                print(f"DEBUG: Connectivity validation exception: {e}")
        
        return result
    
    def validate_calculation_ranges(self, path_data: Dict[str, Any]) -> ValidationResult:
        """Validate calculation input ranges"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])
        
        try:
            # Validate source component
            source = path_data.get('source_component', {})
            if source:
                noise_level = source.get('noise_level')
                if noise_level and (noise_level < 30 or noise_level > 120):
                    result.add_warning(f"Source noise level ({noise_level} dB) outside typical range (30-120 dB)")
            
            # Validate segments
            segments = path_data.get('segments', [])
            for i, segment in enumerate(segments):
                # Validate airflow
                airflow = segment.get('airflow_cfm', 0)
                if airflow < 50:
                    result.add_warning(f"Segment {i+1} airflow ({airflow} CFM) is very low")
                elif airflow > 20000:
                    result.add_warning(f"Segment {i+1} airflow ({airflow} CFM) is very high")
                
                # Validate duct dimensions
                width = segment.get('duct_width', 0)
                height = segment.get('duct_height', 0)
                
                if width and height:
                    area = width * height / 144  # Convert to sq ft
                    if area > 0:
                        velocity = airflow / area / 60  # fpm
                        if velocity < 100:
                            result.add_info(f"Segment {i+1} velocity ({velocity:.0f} fpm) is low")
                        elif velocity > 4000:
                            result.add_warning(f"Segment {i+1} velocity ({velocity:.0f} fpm) is very high")
            
        except Exception as e:
            result.add_error(f"Range validation failed: {e}")
        
        return result
