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
    
    def validate_path_element(self, element_data: Dict[str, Any], element_type: str) -> ValidationResult:
        """Comprehensive validation for path elements before calculation"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])
        
        try:
            # Required fields validation
            if element_type == 'source':
                self._validate_source_element(element_data, result)
            elif element_type == 'duct':
                self._validate_duct_element(element_data, result)
            elif element_type in ['elbow', 'junction']:
                self._validate_fitting_element(element_data, result)
            elif element_type == 'terminal':
                self._validate_terminal_element(element_data, result)
            
            # Physical constraints validation
            self._validate_physical_constraints(element_data, result)
            
        except Exception as e:
            result.add_error(f"Element validation failed: {e}")
        
        return result
    
    def _validate_source_element(self, element_data: Dict[str, Any], result: ValidationResult):
        """Validate source element data"""
        # Check octave band levels
        octave_bands = element_data.get('octave_band_levels')
        if octave_bands:
            if not isinstance(octave_bands, list) or len(octave_bands) != 8:
                result.add_error("Source octave band levels must be a list of 8 values")
            else:
                # Validate individual band levels
                for i, level in enumerate(octave_bands):
                    if not isinstance(level, (int, float)):
                        result.add_error(f"Octave band {i+1} level must be numeric, got {type(level)}")
                    elif level < 0 or level > 150:
                        result.add_warning(f"Octave band {i+1} level ({level} dB) outside typical range (0-150 dB)")
        
        # Check A-weighted level consistency
        noise_level = element_data.get('noise_level')
        if noise_level is not None:
            if not isinstance(noise_level, (int, float)):
                result.add_error(f"Source noise level must be numeric, got {type(noise_level)}")
            elif noise_level < 20 or noise_level > 140:
                result.add_warning(f"Source noise level ({noise_level} dBA) outside typical range (20-140 dBA)")
    
    def _validate_duct_element(self, element_data: Dict[str, Any], result: ValidationResult):
        """Validate duct element data"""
        # Length validation
        length = element_data.get('length', 0)
        if not isinstance(length, (int, float)) or length <= 0:
            result.add_error(f"Duct length must be positive, got {length}")
        elif length > 1000:
            result.add_warning(f"Duct length ({length} ft) is unusually long")
        
        # Dimension validation
        duct_shape = element_data.get('duct_shape', 'rectangular').lower()
        if duct_shape == 'rectangular':
            width = element_data.get('width', 0)
            height = element_data.get('height', 0)
            
            if not isinstance(width, (int, float)) or width <= 0:
                result.add_error(f"Duct width must be positive, got {width}")
            elif width > 120:
                result.add_warning(f"Duct width ({width} in) is unusually large")
            
            if not isinstance(height, (int, float)) or height <= 0:
                result.add_error(f"Duct height must be positive, got {height}")
            elif height > 120:
                result.add_warning(f"Duct height ({height} in) is unusually large")
                
        elif duct_shape == 'circular':
            diameter = element_data.get('diameter', 0)
            if not isinstance(diameter, (int, float)) or diameter <= 0:
                result.add_error(f"Duct diameter must be positive, got {diameter}")
            elif diameter > 120:
                result.add_warning(f"Duct diameter ({diameter} in) is unusually large")
    
    def _validate_fitting_element(self, element_data: Dict[str, Any], result: ValidationResult):
        """Validate fitting element data (elbows, junctions)"""
        # Flow rate validation
        flow_rate = element_data.get('flow_rate', 0)
        if not isinstance(flow_rate, (int, float)) or flow_rate <= 0:
            result.add_error(f"Fitting flow rate must be positive, got {flow_rate}")
        elif flow_rate > 50000:
            result.add_warning(f"Flow rate ({flow_rate} CFM) is very high")
        
        # Pressure drop validation
        pressure_drop = element_data.get('pressure_drop')
        if pressure_drop is not None:
            if not isinstance(pressure_drop, (int, float)) or pressure_drop < 0:
                result.add_error(f"Pressure drop must be non-negative, got {pressure_drop}")
            elif pressure_drop > 5.0:
                result.add_warning(f"Pressure drop ({pressure_drop} in. w.g.) is very high")
    
    def _validate_terminal_element(self, element_data: Dict[str, Any], result: ValidationResult):
        """Validate terminal element data"""
        # Room correction parameters
        room_volume = element_data.get('room_volume')
        if room_volume is not None:
            if not isinstance(room_volume, (int, float)) or room_volume <= 0:
                result.add_error(f"Room volume must be positive, got {room_volume}")
            elif room_volume > 1000000:
                result.add_warning(f"Room volume ({room_volume} ft³) is very large")
        
        room_absorption = element_data.get('room_absorption')
        if room_absorption is not None:
            if not isinstance(room_absorption, (int, float)) or room_absorption <= 0:
                result.add_error(f"Room absorption must be positive, got {room_absorption}")
    
    def _validate_physical_constraints(self, element_data: Dict[str, Any], result: ValidationResult):
        """Validate physical constraints and relationships"""
        # Flow velocity validation
        flow_rate = element_data.get('flow_rate')
        width = element_data.get('width')
        height = element_data.get('height')
        diameter = element_data.get('diameter')
        
        if flow_rate and isinstance(flow_rate, (int, float)) and flow_rate > 0:
            area = None
            if width and height:
                area = (width * height) / 144  # Convert to sq ft
            elif diameter:
                area = 3.14159 * (diameter/24)**2  # Convert to sq ft
            
            if area and area > 0:
                velocity = flow_rate / area
                if velocity < 100:
                    result.add_info(f"Low air velocity ({velocity:.0f} fpm) - check for oversized ductwork")
                elif velocity > 6000:
                    result.add_warning(f"Very high air velocity ({velocity:.0f} fpm) - noise and pressure issues likely")
    
    def validate_calculation_inputs(self, path_data: Dict[str, Any]) -> ValidationResult:
        """Comprehensive validation of all calculation inputs"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])
        
        try:
            # Validate overall path structure
            if not isinstance(path_data, dict):
                result.add_error(f"Path data must be a dictionary, got {type(path_data)}")
                return result
            
            # Validate source component
            source_component = path_data.get('source_component')
            if not source_component:
                result.add_error("Missing source component")
            else:
                source_validation = self.validate_path_element(source_component, 'source')
                result.merge(source_validation)
            
            # Validate segments
            segments = path_data.get('segments', [])
            if not segments:
                result.add_warning("No segments in path")
            else:
                for i, segment in enumerate(segments):
                    if not isinstance(segment, dict):
                        result.add_error(f"Segment {i+1} must be a dictionary")
                        continue
                    
                    segment_validation = self.validate_path_element(segment, 'duct')
                    result.merge(segment_validation)
                    
                    # Check for fittings
                    fittings = segment.get('fittings', [])
                    for j, fitting in enumerate(fittings):
                        fitting_type = fitting.get('fitting_type', 'unknown')
                        fitting_validation = self.validate_path_element(fitting, fitting_type)
                        result.merge(fitting_validation)
            
            # Validate terminal component
            terminal_component = path_data.get('terminal_component')
            if terminal_component:
                terminal_validation = self.validate_path_element(terminal_component, 'terminal')
                result.merge(terminal_validation)
            
            # Cross-validate path consistency
            self._validate_path_consistency(path_data, result)
            
        except Exception as e:
            result.add_error(f"Input validation failed: {e}")
        
        return result
    
    def _validate_path_consistency(self, path_data: Dict[str, Any], result: ValidationResult):
        """Validate consistency across the entire path"""
        segments = path_data.get('segments', [])
        
        # Check flow rate consistency
        flow_rates = []
        for segment in segments:
            flow_rate = segment.get('flow_rate')
            if flow_rate and isinstance(flow_rate, (int, float)):
                flow_rates.append(flow_rate)
        
        if len(flow_rates) > 1:
            max_flow = max(flow_rates)
            min_flow = min(flow_rates)
            if max_flow > 0 and (max_flow - min_flow) / max_flow > 0.5:
                result.add_warning(f"Large flow rate variation in path: {min_flow:.0f} to {max_flow:.0f} CFM")
        
        # Check duct sizing consistency
        areas = []
        for segment in segments:
            width = segment.get('width')
            height = segment.get('height')
            diameter = segment.get('diameter')
            
            if width and height:
                area = width * height
            elif diameter:
                area = 3.14159 * (diameter/2)**2
            else:
                continue
            
            areas.append(area)
        
        if len(areas) > 1:
            max_area = max(areas)
            min_area = min(areas)
            if max_area > 0 and (max_area - min_area) / max_area > 0.8:
                result.add_info("Significant duct size changes detected - verify transitions are properly modeled")
