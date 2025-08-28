"""
Path Data Builder - Refactored components for building HVAC path data
Breaks down large methods into focused, testable components
"""

from typing import Dict, List, Optional, Any
import json
from sqlalchemy.orm import Session

from models.hvac import HVACPath, HVACSegment
from models.mechanical import MechanicalUnit
from .hvac_constants import NUM_OCTAVE_BANDS, FREQUENCY_BAND_LABELS


class SourceComponentBuilder:
    """Handles building source component data with mechanical unit integration"""
    
    def __init__(self, debug_logger, mechanical_unit_finder):
        self.debug_logger = debug_logger
        self.find_mechanical_unit = mechanical_unit_finder
    
    def build_source_from_component(self, source_comp, hvac_path, session) -> Dict:
        """Build source component data from HVACComponent"""
        source_data = {
            'component_type': source_comp.component_type,
            'noise_level': source_comp.noise_level
        }
        
        # Try to enrich with mechanical unit spectrum
        try:
            unit = self.find_mechanical_unit(source_comp, getattr(hvac_path, 'project_id', None))
            if unit:
                octave_bands = self._extract_unit_spectrum(unit)
                source_data['octave_band_levels'] = octave_bands
                self.debug_logger.info('PathBuilder', 
                    f"Enriched source from mechanical unit '{unit.name}'", 
                    {'octave_bands': octave_bands})
        except Exception as e:
            self.debug_logger.warning('PathBuilder', 
                "Failed to enrich source with mechanical unit bands", error=e)
        
        return source_data
    
    def build_source_from_mechanical_unit(self, unit: MechanicalUnit) -> Dict:
        """Build source component data from MechanicalUnit"""
        octave_bands = self._extract_unit_spectrum(unit)
        noise_level = getattr(unit, 'base_noise_dba', None)
        
        source_data = {
            'component_type': getattr(unit, 'unit_type', None) or 'unit',
            'noise_level': noise_level,
            'octave_band_levels': octave_bands,
        }
        
        self.debug_logger.info('PathBuilder', 
            f"Using mechanical unit '{unit.name}' as source", 
            {'noise_dba': noise_level, 'octave_bands': octave_bands})
        
        return source_data
    
    def build_fallback_source(self, first_segment) -> Dict:
        """Build source from first segment's from_component (fallback)"""
        if not first_segment.from_component:
            return None
        
        comp = first_segment.from_component
        
        self.debug_logger.debug('PathBuilder', 
            "Using from_component as fallback source", {
                'comp_id': getattr(comp, 'id', None),
                'name': getattr(comp, 'name', None),
                'type': getattr(comp, 'component_type', None),
                'noise_level': getattr(comp, 'noise_level', None),
            })
        
        return {
            'component_type': comp.component_type,
            'noise_level': comp.noise_level
        }
    
    def _extract_unit_spectrum(self, unit: MechanicalUnit) -> Optional[List[float]]:
        """Extract octave band spectrum from mechanical unit JSON data"""
        # Try different spectrum sources in order of preference
        for source_attr, source_name in [
            ('outlet_levels_json', 'outlet'),
            ('inlet_levels_json', 'inlet'),
            ('radiated_levels_json', 'radiated')
        ]:
            json_data = getattr(unit, source_attr, None)
            if json_data:
                try:
                    data = json.loads(json_data)
                    octave_bands = None
                    
                    # Handle dictionary format
                    if hasattr(data, 'get'):
                        octave_bands = [float(data.get(k, 0) or 0) for k in FREQUENCY_BAND_LABELS]
                    # Handle list format
                    elif isinstance(data, list) and len(data) >= NUM_OCTAVE_BANDS:
                        octave_bands = [float(x or 0) for x in data[:NUM_OCTAVE_BANDS]]
                    
                    if octave_bands:
                        self.debug_logger.debug('PathBuilder', 
                            f"Extracted spectrum from {source_name}", 
                            {'octave_bands': octave_bands})
                        return octave_bands
                        
                except Exception as e:
                    self.debug_logger.warning('PathBuilder', 
                        f"Failed to parse {source_name} spectrum JSON", error=e)
        
        return None


class PathValidator:
    """Handles validation of path data during construction"""
    
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger
    
    def validate_source_spectrum(self, source_component: Dict) -> bool:
        """Validate that source has required octave band spectrum"""
        bands = source_component.get('octave_band_levels')
        valid_bands = (isinstance(bands, list) and 
                      len(bands) == NUM_OCTAVE_BANDS and 
                      any(isinstance(b, (int, float)) for b in bands))
        
        if not valid_bands:
            self.debug_logger.warning('PathBuilder', 
                "Source missing valid octave band spectrum", 
                {'source_component': source_component})
            return False
        
        return True
    
    def validate_path_completeness(self, path_data: Dict) -> bool:
        """Validate that path data has all required components"""
        required_keys = ['source_component', 'segments']
        
        for key in required_keys:
            if key not in path_data:
                self.debug_logger.error('PathBuilder', 
                    f"Path data missing required key: {key}")
                return False
        
        # Check segments not empty
        if not path_data['segments']:
            self.debug_logger.error('PathBuilder', 
                "Path has no segments")
            return False
        
        return True
    
    def run_range_validation(self, path_data: Dict, validation_framework):
        """Run range validation on path data"""
        try:
            range_validation = validation_framework.validate_calculation_ranges(path_data)
            path_data['validation_result'] = range_validation
            
            if range_validation.has_messages():
                self.debug_logger.info('PathBuilder', 
                    "Path data range validation completed", {
                        'errors': range_validation.errors,
                        'warnings': range_validation.warnings
                    })
        except Exception as e:
            self.debug_logger.error('PathBuilder', 
                "Range validation failed", error=e)


class SegmentProcessor:
    """Handles processing of HVAC segments"""
    
    def __init__(self, debug_logger, segment_data_builder):
        self.debug_logger = debug_logger
        self.build_segment_data = segment_data_builder
    
    def process_segments(self, segments: List[HVACSegment]) -> List[Dict]:
        """Process all segments and return segment data list"""
        segment_data_list = []
        
        for segment in segments:
            try:
                segment_data = self.build_segment_data(segment)
                segment_data_list.append(segment_data)
            except Exception as e:
                self.debug_logger.error('PathBuilder', 
                    f"Failed to process segment {getattr(segment, 'id', 'unknown')}", 
                    error=e)
                # Add placeholder segment to maintain order
                segment_data_list.append({
                    'length': 0.0,
                    'duct_width': 12.0,
                    'duct_height': 8.0,
                    'error': str(e)
                })
        
        self.debug_logger.info('PathBuilder', 
            f"Processed {len(segment_data_list)} segments")
        
        return segment_data_list


class PathDataBuilder:
    """Main orchestrator for building path data"""
    
    def __init__(self, debug_logger, segment_data_builder, mechanical_unit_finder):
        self.debug_logger = debug_logger
        self.source_builder = SourceComponentBuilder(debug_logger, mechanical_unit_finder)
        self.validator = PathValidator(debug_logger)
        self.segment_processor = SegmentProcessor(debug_logger, segment_data_builder)
    
    def build_path_data(self, hvac_path: HVACPath, segments: List[HVACSegment], 
                       validation_framework, session: Session) -> Optional[Dict]:
        """
        Build complete path data from HVAC path and segments.
        
        This is the refactored version of _build_path_data_within_session,
        broken down into focused, testable components.
        """
        path_data = {
            'source_component': {},
            'segments': [],
            'terminal_component': {}
        }
        
        # Step 1: Build source component data
        source_data = self._build_source_component(hvac_path, segments, session)
        if not source_data:
            self.debug_logger.error('PathBuilder', 
                "Failed to build source component data")
            return None
        
        path_data['source_component'] = source_data
        
        # Step 2: Validate source spectrum
        if not self.validator.validate_source_spectrum(source_data):
            return None
        
        # Step 3: Process segments
        segment_data_list = self.segment_processor.process_segments(segments)
        path_data['segments'] = segment_data_list
        
        # Step 4: Build terminal component (if exists)
        terminal_data = self._build_terminal_component(hvac_path)
        if terminal_data:
            path_data['terminal_component'] = terminal_data
        
        # Step 5: Run validation
        if not self.validator.validate_path_completeness(path_data):
            return None
        
        self.validator.run_range_validation(path_data, validation_framework)
        
        self.debug_logger.info('PathBuilder', 
            "Successfully built path data", {
                'segments_count': len(segment_data_list),
                'has_terminal': bool(terminal_data)
            })
        
        return path_data
    
    def _build_source_component(self, hvac_path: HVACPath, segments: List[HVACSegment], 
                               session: Session) -> Optional[Dict]:
        """Build source component data with fallback strategies"""
        # Strategy 1: Use explicit primary_source
        source_comp = getattr(hvac_path, 'primary_source', None)
        if source_comp:
            return self.source_builder.build_source_from_component(source_comp, hvac_path, session)
        
        # Strategy 2: Use linked mechanical unit
        if getattr(hvac_path, 'primary_source_id', None):
            unit = session.query(MechanicalUnit).filter(
                MechanicalUnit.id == hvac_path.primary_source_id
            ).first()
            
            if unit:
                return self.source_builder.build_source_from_mechanical_unit(unit)
        
        # Strategy 3: Use first segment's from_component
        if segments:
            fallback_source = self.source_builder.build_fallback_source(segments[0])
            if fallback_source:
                return fallback_source
        
        self.debug_logger.error('PathBuilder', 
            "No valid source component found")
        return None
    
    def _build_terminal_component(self, hvac_path: HVACPath) -> Optional[Dict]:
        """Build terminal component data if target space exists"""
        target_space = getattr(hvac_path, 'target_space', None)
        if target_space:
            return {
                'room_volume': getattr(target_space, 'volume', 1000.0),
                'room_absorption': getattr(target_space, 'total_absorption', 100.0)
            }
        return None