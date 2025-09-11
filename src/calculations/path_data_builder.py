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
        
        # Enhanced debugging for source component
        print("--------------------------------")
        print("DEBUG_SOURCE: Building source component data from HVACComponent")
        print("--------------------------------")
        print(f"DEBUG_SOURCE: Source component object:")
        print(f"DEBUG_SOURCE:   Type: {type(source_comp)}")
        print(f"DEBUG_SOURCE:   ID: {getattr(source_comp, 'id', 'None')}")
        print(f"DEBUG_SOURCE:   Name: {getattr(source_comp, 'name', 'None')}")
        print(f"DEBUG_SOURCE:   Component type: {getattr(source_comp, 'component_type', 'None')}")
        print(f"DEBUG_SOURCE:   Noise level: {getattr(source_comp, 'noise_level', 'None')}")
        print(f"DEBUG_SOURCE:   CFM attribute: {getattr(source_comp, 'cfm', 'None')}")
        print(f"DEBUG_SOURCE:   Has CFM attr: {hasattr(source_comp, 'cfm')}")
        print(f"DEBUG_SOURCE:   All attributes: {[attr for attr in dir(source_comp) if not attr.startswith('_')]}")
        
        # Try to refresh the object from database
        try:
            session.refresh(source_comp)
            print(f"DEBUG_SOURCE: After refresh - CFM: {getattr(source_comp, 'cfm', 'None')}")
        except Exception as e:
            print(f"DEBUG_SOURCE: Could not refresh object: {e}")
        
        # Try direct database query
        try:
            from models.hvac import HVACComponent
            db_comp = session.query(HVACComponent).filter(HVACComponent.id == source_comp.id).first()
            if db_comp:
                print(f"DEBUG_SOURCE: Direct DB query - CFM: {db_comp.cfm}")
            else:
                print(f"DEBUG_SOURCE: Direct DB query - Component not found")
        except Exception as e:
            print(f"DEBUG_SOURCE: Direct DB query failed: {e}")
        
        # Try multiple approaches to get CFM value
        cfm_value = None
        
        # Approach 1: Direct attribute access
        cfm_value = getattr(source_comp, 'cfm', None)
        print(f"DEBUG_SOURCE: Approach 1 (direct attr) - CFM: {cfm_value}")
        
        # Approach 2: Try direct database query if not found
        if cfm_value is None:
            try:
                from models.hvac import HVACComponent
                db_comp = session.query(HVACComponent).filter(HVACComponent.id == source_comp.id).first()
                if db_comp:
                    cfm_value = db_comp.cfm
                    print(f"DEBUG_SOURCE: Approach 2 (direct DB query) - CFM: {cfm_value}")
            except Exception as e:
                print(f"DEBUG_SOURCE: Approach 2 failed: {e}")
        
        # Approach 3: Try accessing via __dict__ if still not found
        if cfm_value is None:
            try:
                cfm_value = source_comp.__dict__.get('cfm')
                print(f"DEBUG_SOURCE: Approach 3 (__dict__) - CFM: {cfm_value}")
            except Exception as e:
                print(f"DEBUG_SOURCE: Approach 3 failed: {e}")
        
        source_data = {
            'component_type': source_comp.component_type,
            'noise_level': source_comp.noise_level,
            'flow_rate': cfm_value  # Include CFM from source component
        }
        
        # Debug CFM assignment
        cfm_value = source_data.get('flow_rate')
        print(f"DEBUG_SOURCE: Final source_data: {source_data}")
        if cfm_value:
            self.debug_logger.info('PathBuilder', 
                f"Source component CFM assigned: {cfm_value} CFM", 
                {'component_type': source_comp.component_type, 'cfm': cfm_value})
        else:
            self.debug_logger.warning('PathBuilder', 
                f"Source component has no CFM value, will use defaults", 
                {'component_type': source_comp.component_type})
        
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
        
        # Enhanced debugging for fallback source component
        print("--------------------------------")
        print("DEBUG_FALLBACK: Building fallback source component data from HVACComponent")
        print("--------------------------------")
        print(f"DEBUG_FALLBACK: Fallback source component object:")
        print(f"DEBUG_FALLBACK:   Type: {type(comp)}")
        print(f"DEBUG_FALLBACK:   ID: {getattr(comp, 'id', 'None')}")
        print(f"DEBUG_FALLBACK:   Name: {getattr(comp, 'name', 'None')}")
        print(f"DEBUG_FALLBACK:   Component type: {getattr(comp, 'component_type', 'None')}")
        print(f"DEBUG_FALLBACK:   Noise level: {getattr(comp, 'noise_level', 'None')}")
        print(f"DEBUG_FALLBACK:   CFM attribute: {getattr(comp, 'cfm', 'None')}")
        print(f"DEBUG_FALLBACK:   Has CFM attr: {hasattr(comp, 'cfm')}")
        print(f"DEBUG_FALLBACK:   All attributes: {[attr for attr in dir(comp) if not attr.startswith('_')]}")
        
        # Try to refresh the object from database
        try:
            # Get session from the segment's relationship
            session = comp._sa_instance_state.session
            session.refresh(comp)
            print(f"DEBUG_FALLBACK: After refresh - CFM: {getattr(comp, 'cfm', 'None')}")
        except Exception as e:
            print(f"DEBUG_FALLBACK: Could not refresh object: {e}")
        
        # Try direct database query
        try:
            from models.hvac import HVACComponent
            session = comp._sa_instance_state.session
            db_comp = session.query(HVACComponent).filter(HVACComponent.id == comp.id).first()
            if db_comp:
                print(f"DEBUG_FALLBACK: Direct DB query - CFM: {db_comp.cfm}")
            else:
                print(f"DEBUG_FALLBACK: Direct DB query - Component not found")
        except Exception as e:
            print(f"DEBUG_FALLBACK: Direct DB query failed: {e}")
        
        self.debug_logger.debug('PathBuilder', 
            "Using from_component as fallback source", {
                'comp_id': getattr(comp, 'id', None),
                'name': getattr(comp, 'name', None),
                'type': getattr(comp, 'component_type', None),
                'noise_level': getattr(comp, 'noise_level', None),
            })
        
        # Try multiple approaches to get CFM value
        cfm_value = None
        
        # Approach 1: Direct attribute access
        cfm_value = getattr(comp, 'cfm', None)
        print(f"DEBUG_FALLBACK: Approach 1 (direct attr) - CFM: {cfm_value}")
        
        # Approach 2: Try direct database query if not found
        if cfm_value is None:
            try:
                from models.hvac import HVACComponent
                session = comp._sa_instance_state.session
                db_comp = session.query(HVACComponent).filter(HVACComponent.id == comp.id).first()
                if db_comp:
                    cfm_value = db_comp.cfm
                    print(f"DEBUG_FALLBACK: Approach 2 (direct DB query) - CFM: {cfm_value}")
            except Exception as e:
                print(f"DEBUG_FALLBACK: Approach 2 failed: {e}")
        
        # Approach 3: Try accessing via __dict__ if still not found
        if cfm_value is None:
            try:
                cfm_value = comp.__dict__.get('cfm')
                print(f"DEBUG_FALLBACK: Approach 3 (__dict__) - CFM: {cfm_value}")
            except Exception as e:
                print(f"DEBUG_FALLBACK: Approach 3 failed: {e}")
        
        source_data = {
            'component_type': comp.component_type,
            'noise_level': comp.noise_level,
            'flow_rate': cfm_value  # Include CFM from fallback component
        }
        
        # Debug CFM assignment for fallback
        cfm_value = source_data.get('flow_rate')
        print(f"DEBUG_FALLBACK: Final fallback source_data: {source_data}")
        if cfm_value:
            self.debug_logger.info('PathBuilder', 
                f"Fallback source component CFM assigned: {cfm_value} CFM", 
                {'component_type': comp.component_type, 'cfm': cfm_value})
        else:
            self.debug_logger.warning('PathBuilder', 
                f"Fallback source component has no CFM value, will use defaults", 
                {'component_type': comp.component_type})
        
        return source_data
    
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
        print(f"DEBUG_SOURCE_BUILD: Building source component for path {getattr(hvac_path, 'id', 'unknown')}")
        
        # Strategy 1: Use explicit primary_source
        source_comp = getattr(hvac_path, 'primary_source', None)
        print(f"DEBUG_SOURCE_BUILD: Strategy 1 - primary_source: {source_comp}")
        if source_comp:
            print(f"DEBUG_SOURCE_BUILD: Using Strategy 1 - primary_source")
            return self.source_builder.build_source_from_component(source_comp, hvac_path, session)
        
        # Strategy 2: Use linked mechanical unit
        primary_source_id = getattr(hvac_path, 'primary_source_id', None)
        print(f"DEBUG_SOURCE_BUILD: Strategy 2 - primary_source_id: {primary_source_id}")
        if primary_source_id:
            unit = session.query(MechanicalUnit).filter(
                MechanicalUnit.id == primary_source_id
            ).first()
            print(f"DEBUG_SOURCE_BUILD: Found mechanical unit: {unit}")
            if unit:
                print(f"DEBUG_SOURCE_BUILD: Using Strategy 2 - mechanical unit")
                return self.source_builder.build_source_from_mechanical_unit(unit)
        
        # Strategy 3: Use first segment's from_component
        print(f"DEBUG_SOURCE_BUILD: Strategy 3 - first segment from_component")
        print(f"DEBUG_SOURCE_BUILD: Number of segments: {len(segments) if segments else 0}")
        if segments:
            print(f"DEBUG_SOURCE_BUILD: First segment from_component: {getattr(segments[0], 'from_component', None)}")
            fallback_source = self.source_builder.build_fallback_source(segments[0])
            if fallback_source:
                print(f"DEBUG_SOURCE_BUILD: Using Strategy 3 - fallback source")
                return fallback_source
        
        print(f"DEBUG_SOURCE_BUILD: No valid source component found")
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