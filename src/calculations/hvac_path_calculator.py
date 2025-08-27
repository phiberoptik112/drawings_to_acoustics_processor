"""
HVAC Path Calculator - Complete HVAC path noise analysis system
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from models import get_session
from models.hvac import HVACPath, HVACSegment, HVACComponent, SegmentFitting
from sqlalchemy.orm import selectinload
from models.mechanical import MechanicalUnit
from data.components import STANDARD_COMPONENTS, STANDARD_FITTINGS
from src.calculations.noise_calculator import NoiseCalculator
# Debug export imports
import os
from datetime import datetime
import json as _json
import csv as _csv
from utils import get_user_data_directory


@dataclass
class PathAnalysisResult:
    """Result of HVAC path analysis"""
    path_id: int
    path_name: str
    source_noise: float
    terminal_noise: float
    total_attenuation: float
    nc_rating: int
    calculation_valid: bool
    segment_results: List[Dict]
    warnings: List[str]
    error_message: Optional[str] = None
    debug_log: Optional[List[Dict]] = None


class HVACPathCalculator:
    """Comprehensive HVAC path noise calculation and management system"""
    
    def __init__(self, project_id: int = None):
        """Initialize the HVAC path calculator"""
        self.project_id = project_id
        self.noise_calculator = NoiseCalculator()
        # Debug export switch via environment variable HVAC_DEBUG_EXPORT
        env_val = str(os.environ.get("HVAC_DEBUG_EXPORT", "")).strip().lower()
        self.debug_export_enabled = env_val in {"1", "true", "yes", "on"}
    
    def create_hvac_path_from_drawing(self, project_id: int, drawing_data: Dict) -> Optional[HVACPath]:
        """
        Create HVAC path from drawing elements (components and segments)
        
        Args:
            project_id: Project ID
            drawing_data: Dictionary containing components and segments from drawing
            
        Returns:
            Created HVACPath or None if creation failed
        """
        session = None
        try:
            components = drawing_data.get('components', [])
            segments = drawing_data.get('segments', [])
            
            if len(components) < 2:
                raise ValueError("Need at least 2 components to create HVAC path")
            
            if len(segments) == 0:
                raise ValueError("Need at least 1 segment to connect components")
            
            from models.database import get_hvac_session
            with get_hvac_session() as session:
                # Create HVAC components in database with auto-linking to mechanical units
                db_components = {}
                for comp_data in components:
                    hvac_comp = HVACComponent(
                        project_id=project_id,
                        drawing_id=comp_data.get('drawing_id', 0),
                        name=f"{comp_data.get('component_type', 'unknown').upper()}-{len(db_components)+1}",
                        component_type=comp_data.get('component_type', 'unknown'),
                        x_position=comp_data.get('x', 0),
                        y_position=comp_data.get('y', 0),
                        noise_level=self.get_component_noise_level(comp_data.get('component_type', ''))
                    )
                    session.add(hvac_comp)
                    session.flush()  # Get ID
                    
                    # Auto-link with mechanical unit if possible
                    try:
                        matched_unit = self.find_matching_mechanical_unit(hvac_comp, project_id)
                        if matched_unit:
                            # Store reference for path primary source if this is first component (likely source)
                            if len(db_components) == 0:
                                import os
                                if os.environ.get('HVAC_DEBUG_EXPORT'):
                                    print(f"DEBUG: Linking primary source component '{hvac_comp.name}' to mechanical unit '{matched_unit.name}'")
                    except Exception as e:
                        import os
                        if os.environ.get('HVAC_DEBUG_EXPORT'):
                            print(f"DEBUG: Auto-linking failed for component '{hvac_comp.name}': {e}")
                    
                    db_components[len(db_components)] = hvac_comp
                
                # Create HVAC path with mechanical unit integration
                source_comp = db_components[0]
                terminal_comp = db_components[len(db_components)-1]
                
                # Try to find mechanical unit for primary source
                primary_source_unit_id = None
                try:
                    matched_unit = self.find_matching_mechanical_unit(source_comp, project_id)
                    if matched_unit:
                        primary_source_unit_id = matched_unit.id
                        import os
                        if os.environ.get('HVAC_DEBUG_EXPORT'):
                            print(f"DEBUG: Setting path primary source to mechanical unit '{matched_unit.name}' (ID: {matched_unit.id})")
                except Exception as e:
                    import os
                    if os.environ.get('HVAC_DEBUG_EXPORT'):
                        print(f"DEBUG: Could not link path to mechanical unit: {e}")
                
                hvac_path = HVACPath(
                    project_id=project_id,
                    name=f"Path: {source_comp.component_type.upper()} to {terminal_comp.component_type.upper()}",
                    description=f"HVAC path from {source_comp.name} to {terminal_comp.name}",
                    path_type='supply',
                    primary_source_id=primary_source_unit_id  # Link to mechanical unit if found
                )
                session.add(hvac_path)
                session.flush()  # Get ID
                
                # Create segments using actual connections from drawing
                created_segments: List[HVACSegment] = []
                for i, seg_data in enumerate(segments):
                    # Find the actual connected components
                    from_comp_id = None
                    to_comp_id = None
                    
                    # Find from_component
                    if seg_data.get('from_component'):
                        from_comp_data = seg_data['from_component']
                        for comp_idx, db_comp in db_components.items():
                            if (db_comp.x_position == from_comp_data.get('x', 0) and 
                                db_comp.y_position == from_comp_data.get('y', 0) and
                                db_comp.component_type == from_comp_data.get('component_type', 'unknown')):
                                from_comp_id = db_comp.id
                                break
                    
                    # Find to_component
                    if seg_data.get('to_component'):
                        to_comp_data = seg_data['to_component']
                        for comp_idx, db_comp in db_components.items():
                            if (db_comp.x_position == to_comp_data.get('x', 0) and 
                                db_comp.y_position == to_comp_data.get('y', 0) and
                                db_comp.component_type == to_comp_data.get('component_type', 'unknown')):
                                to_comp_id = db_comp.id
                                break
                    
                    # Only create segment if we have at least one connection
                    if from_comp_id or to_comp_id:
                        hvac_segment = HVACSegment(
                            hvac_path_id=hvac_path.id,
                            from_component_id=from_comp_id,
                            to_component_id=to_comp_id,
                            length=seg_data.get('length_real', 0),
                            segment_order=i+1,
                            duct_width=12,  # Default rectangular duct
                            duct_height=8,
                            duct_shape='rectangular',
                            duct_type='sheet_metal'
                        )
                        session.add(hvac_segment)
                        created_segments.append(hvac_segment)
                    else:
                        # Fallback: if neither endpoint matched by exact equality, try position/type match
                        # to be resilient to dict identity differences between overlay and calculator
                        fc = seg_data.get('from_component') or {}
                        tc = seg_data.get('to_component') or {}
                        def match_id_by_pos(cdict):
                            for _, db_comp in db_components.items():
                                if (db_comp.x_position == cdict.get('x', 0) and
                                    db_comp.y_position == cdict.get('y', 0) and
                                    db_comp.component_type == cdict.get('component_type', 'unknown')):
                                    return db_comp.id
                            return None
                        from_comp_id = match_id_by_pos(fc)
                        to_comp_id = match_id_by_pos(tc)
                        if from_comp_id or to_comp_id:
                            hvac_segment = HVACSegment(
                                hvac_path_id=hvac_path.id,
                                from_component_id=from_comp_id,
                                to_component_id=to_comp_id,
                                length=seg_data.get('length_real', 0),
                                segment_order=i+1,
                                duct_width=12,
                                duct_height=8,
                                duct_shape='rectangular',
                                duct_type='sheet_metal'
                            )
                            session.add(hvac_segment)
                            created_segments.append(hvac_segment)
                
                # Reorder segments by connectivity from source to terminal
                try:
                    ordered = self._order_segments_by_connectivity(created_segments, preferred_source_component_id=getattr(source_comp, 'id', None))
                    for idx, seg in enumerate(ordered):
                        seg.segment_order = idx + 1
                    print(f"DEBUG: Reordered {len(ordered)} segments by connectivity from source -> terminal")
                except Exception as e:
                    print(f"DEBUG: Failed to reorder segments by connectivity: {e}")

                
                # Session commit handled by context manager
                
                # Calculate noise for the new path (uses any saved source/receiver if available later)
                self.calculate_path_noise(hvac_path.id)
                
                return hvac_path
            
        except Exception as e:
            print(f"Error creating HVAC path: {e}")
            return None
    
    def calculate_path_noise(self, path_id: int, debug: bool = False) -> PathAnalysisResult:
        """
        Calculate noise for a specific HVAC path with validation
        
        Args:
            path_id: HVAC path ID
            
        Returns:
            PathAnalysisResult with calculation details
        """
        from src.calculations.hvac_validation import HVACValidationFramework
        
        # Pre-calculation validation
        validation_framework = HVACValidationFramework(self.project_id)
        
        try:
            from models.database import get_hvac_session
            with get_hvac_session() as session:
                path = session.query(HVACPath).filter(HVACPath.id == path_id).first()
                if path:
                    validation_result = validation_framework.validate_path(path)
                    
                    if self.debug_export_enabled:
                        print(f"DEBUG: Pre-calculation validation - Valid: {validation_result.is_valid}")
                        if validation_result.errors:
                            print(f"DEBUG: Validation errors: {validation_result.errors}")
                        if validation_result.warnings:
                            print(f"DEBUG: Validation warnings: {validation_result.warnings}")
                    
                    # Log validation issues but don't stop calculation unless critical
                    if not validation_result.is_valid and any("None" in error or "must have" in error for error in validation_result.errors):
                        print(f"Critical validation failure: {validation_result.errors}")
                        # Return empty result for critical failures - need to check PathAnalysisResult structure
                        pass  # Continue with normal calculation for now
                        
        except Exception as e:
            if self.debug_export_enabled:
                print(f"DEBUG: Validation check failed: {e}")
        
        session = None
        try:
            session = get_session()
            hvac_path = session.query(HVACPath).filter(HVACPath.id == path_id).first()
            
            if not hvac_path:
                raise ValueError(f"HVAC path with ID {path_id} not found")
            
            # Build path data for calculation
            path_data = self.build_path_data_from_db(hvac_path)
            
            if not path_data:
                raise ValueError("Could not build path data from database")
            
            # Perform calculation
            calc_results = self.noise_calculator.calculate_hvac_path_noise(path_data, debug=debug)
            
            # Optional debug export
            try:
                if getattr(self, 'debug_export_enabled', False):
                    self._debug_export_path_result(hvac_path, path_data, calc_results)
            except Exception as e:
                print(f"DEBUG_EXPORT: failed to export debug data for path {hvac_path.id}: {e}")
            
            # Update database with results
            if calc_results['calculation_valid']:
                hvac_path.calculated_noise = calc_results['terminal_noise']
                hvac_path.calculated_nc = calc_results['nc_rating']
                session.commit()
            
            # Create result object
            result = PathAnalysisResult(
                path_id=path_id,
                path_name=hvac_path.name,
                source_noise=calc_results['source_noise'],
                terminal_noise=calc_results['terminal_noise'],
                total_attenuation=calc_results['total_attenuation'],
                nc_rating=calc_results['nc_rating'],
                calculation_valid=calc_results['calculation_valid'],
                segment_results=calc_results['path_segments'],
                warnings=calc_results.get('warnings', []),
                error_message=calc_results.get('error'),
                debug_log=calc_results.get('debug_log')
            )
            
            session.close()
            return result
            
        except Exception as e:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
            return PathAnalysisResult(
                path_id=path_id,
                path_name=f"Path {path_id}",
                source_noise=0,
                terminal_noise=0,
                total_attenuation=0,
                nc_rating=0,
                calculation_valid=False,
                segment_results=[],
                warnings=[],
                error_message=str(e)
            )
    
    def calculate_all_project_paths(self, project_id: int) -> List[PathAnalysisResult]:
        """
        Calculate noise for all HVAC paths in a project
        
        Args:
            project_id: Project ID
            
        Returns:
            List of PathAnalysisResult objects
        """
        results = []
        
        session = None
        try:
            session = get_session()
            hvac_paths = session.query(HVACPath).filter(
                HVACPath.project_id == project_id
            ).all()
            
            for hvac_path in hvac_paths:
                result = self.calculate_path_noise(hvac_path.id)
                results.append(result)
            
            session.close()
            
        except Exception as e:
            print(f"Error calculating project paths: {e}")
        
        return results
    
    def build_path_data_from_db(self, hvac_path: HVACPath) -> Optional[Dict]:
        """
        Build path data structure from database HVAC path
        
        Args:
            hvac_path: HVACPath database object
            
        Returns:
            Path data dictionary for noise calculation
        """
        # Always refetch the path with eager-loaded relationships to avoid
        # lazy-loading on detached instances coming from the UI layer.
        try:
            path_id = getattr(hvac_path, 'id', None) if not isinstance(hvac_path, int) else int(hvac_path)
            if path_id is None:
                raise ValueError("HVACPath id is required to build path data")
            
            from models.database import get_hvac_session
            with get_hvac_session() as session:
                hvac_path = (
                    session.query(HVACPath)
                    .options(
                        selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                        selectinload(HVACPath.segments).selectinload(HVACSegment.to_component),
                        selectinload(HVACPath.segments).selectinload(HVACSegment.fittings),
                        selectinload(HVACPath.primary_source),
                    )
                    .filter(HVACPath.id == path_id)
                    .first()
                )
                
                if not hvac_path:
                    return None
                
                # Build all path data within the session context to avoid detached instances
                return self._build_path_data_within_session(hvac_path, session)
                
        except Exception as e:
            if self.debug_export_enabled:
                print(f"DEBUG: Database path fetch failed: {e}")
            # Fall through and try with the provided object
        
        # Fallback: try to build with the provided object (might be detached)
        return self._build_path_data_fallback(hvac_path)

    def _build_path_data_within_session(self, hvac_path: HVACPath, session) -> Optional[Dict]:
        """Build path data within an active database session to avoid detached instances"""
        try:
            from models.mechanical import MechanicalUnit
            
            path_data = {
                'source_component': {},
                'terminal_component': {},
                'segments': []
            }
            
            segments = hvac_path.segments
            if not segments:
                return None
            
            # Ensure segments are ordered by actual connectivity
            try:
                preferred_source_id = getattr(hvac_path, 'primary_source_id', None)
                segments = self.order_segments_for_path(list(segments), preferred_source_id)
            except Exception as e:
                if self.debug_export_enabled:
                    print(f"DEBUG: Using stored segment order; connectivity ordering failed: {e}")

            # Get source: prefer explicit HVACComponent relationship; fallback to MechanicalUnit id
            source_comp = getattr(hvac_path, 'primary_source', None)
            
            if source_comp is not None:
                path_data['source_component'] = {
                    'component_type': source_comp.component_type,
                    'noise_level': source_comp.noise_level or self.get_component_noise_level(source_comp.component_type)
                }
            else:
                # Mechanical unit lookup using the active session
                unit = None
                if getattr(hvac_path, 'primary_source_id', None):
                    unit = session.query(MechanicalUnit).filter(
                        MechanicalUnit.id == hvac_path.primary_source_id
                    ).first()

                if unit is not None:
                    # Parse outlet spectrum if available
                    octave_bands = None
                    try:
                        import json
                        ob = (getattr(unit, 'outlet_levels_json', None) or 
                              getattr(unit, 'inlet_levels_json', None) or 
                              getattr(unit, 'radiated_levels_json', None))
                        if ob:
                            data = json.loads(ob)
                            order = ["63","125","250","500","1000","2000","4000","8000"]
                            octave_bands = [float(data.get(k, 0) or 0) for k in order]
                    except Exception:
                        octave_bands = None
                    
                    # Derive A-weighted level from spectrum if present
                    noise_level = None
                    if octave_bands:
                        try:
                            noise_level = self.noise_calculator.hvac_engine._calculate_dba_from_spectrum(octave_bands)
                        except Exception:
                            pass
                    noise_level = noise_level or getattr(unit, 'base_noise_dba', None) or 50.0
                    
                    path_data['source_component'] = {
                        'component_type': getattr(unit, 'unit_type', None) or 'unit',
                        'noise_level': noise_level,
                        'octave_band_levels': octave_bands,
                    }
                    
                    if self.debug_export_enabled:
                        print(f"DEBUG: Using mechanical unit '{unit.name}' as source with {noise_level:.1f} dB(A)")
                        if octave_bands:
                            print(f"DEBUG: Octave bands: {octave_bands}")
                else:
                    # Fallback to first segment's from_component
                    first_segment = segments[0]
                    if first_segment.from_component:
                        comp = first_segment.from_component
                        path_data['source_component'] = {
                            'component_type': comp.component_type,
                            'noise_level': comp.noise_level or self.get_component_noise_level(comp.component_type)
                        }
            
            # Get terminal component
            last_segment = segments[-1]
            if last_segment.to_component:
                comp = last_segment.to_component
                path_data['terminal_component'] = {
                    'component_type': comp.component_type,
                    'noise_level': comp.noise_level or self.get_component_noise_level(comp.component_type)
                }
            
            # Convert segments
            for segment in segments:
                segment_data = self._build_segment_data(segment)
                path_data['segments'].append(segment_data)
            
            # Add validation and debug export
            try:
                from src.calculations.hvac_validation import HVACValidationFramework
                validation_framework = HVACValidationFramework(self.project_id)
                range_validation = validation_framework.validate_calculation_ranges(path_data)
                path_data['validation_result'] = range_validation
                
                if self.debug_export_enabled and range_validation.has_messages():
                    print(f"DEBUG: Path data range validation:")
                    if range_validation.errors:
                        print(f"  Errors: {range_validation.errors}")
                    if range_validation.warnings:
                        print(f"  Warnings: {range_validation.warnings}")
            except Exception as e:
                if self.debug_export_enabled:
                    print(f"DEBUG: Range validation failed: {e}")
            
            # Enhanced debug export
            if self.debug_export_enabled:
                self._export_enhanced_debug_data(hvac_path, path_data)
            
            return path_data
            
        except Exception as e:
            if self.debug_export_enabled:
                print(f"DEBUG: Session-based path data building failed: {e}")
            return None

    def _build_path_data_fallback(self, hvac_path: HVACPath) -> Optional[Dict]:
        """Fallback method for building path data with potentially detached instances"""
        try:
            if self.debug_export_enabled:
                print("DEBUG: Using fallback path data building (objects may be detached)")
            
            path_data = {
                'source_component': {'component_type': 'unknown', 'noise_level': 50.0},
                'terminal_component': {'component_type': 'unknown', 'noise_level': 50.0},
                'segments': []
            }
            
            # Try to get basic information without triggering lazy loads
            try:
                if hasattr(hvac_path, 'segments') and hvac_path.segments:
                    for i, segment in enumerate(hvac_path.segments):
                        segment_data = {
                            'length': getattr(segment, 'length', None) or 0,
                            'duct_width': getattr(segment, 'duct_width', None) or 12,
                            'duct_height': getattr(segment, 'duct_height', None) or 8,
                            'duct_shape': getattr(segment, 'duct_shape', None) or 'rectangular',
                            'duct_type': getattr(segment, 'duct_type', None) or 'sheet_metal',
                            'insulation': getattr(segment, 'insulation', None),
                            'lining_thickness': getattr(segment, 'lining_thickness', None) or 0,
                            'fittings': []
                        }
                        path_data['segments'].append(segment_data)
            except Exception as e:
                if self.debug_export_enabled:
                    print(f"DEBUG: Could not extract segment data in fallback: {e}")
            
            return path_data
            
        except Exception as e:
            if self.debug_export_enabled:
                print(f"DEBUG: Fallback path data building failed: {e}")
            return None

    def _build_segment_data(self, segment) -> Dict:
        """Build segment data dictionary from segment object"""
        segment_data = {
            'length': segment.length or 0,
            'duct_width': segment.duct_width or 12,
            'duct_height': segment.duct_height or 8,
            'diameter': getattr(segment, 'diameter', 0) or 0,
            'duct_shape': segment.duct_shape or 'rectangular',
            'duct_type': segment.duct_type or 'sheet_metal',
            'insulation': segment.insulation,
            'lining_thickness': getattr(segment, 'lining_thickness', 0) or 0,
            'fittings': []
        }
        
        # Calculate flow data
        try:
            if (segment_data['duct_shape'] or '').lower() == 'rectangular':
                width_ft = (segment_data['duct_width'] or 0.0) / 12.0
                height_ft = (segment_data['duct_height'] or 0.0) / 12.0
                area_ft2 = max(0.0, width_ft * height_ft)
            else:
                diameter_in = segment_data.get('diameter', 0.0) or 0.0
                radius_ft = (diameter_in / 2.0) / 12.0
                area_ft2 = max(0.0, 3.141592653589793 * radius_ft * radius_ft)
            
            default_velocity_fpm = 800.0
            segment_data['flow_velocity'] = getattr(segment, 'flow_velocity', None) or default_velocity_fpm
            segment_data['flow_rate'] = getattr(segment, 'flow_rate', None) or (area_ft2 * default_velocity_fpm)
        except Exception:
            pass
        
        # Add fittings
        try:
            for fitting in segment.fittings:
                fitting_data = {
                    'fitting_type': fitting.fitting_type,
                    'noise_adjustment': fitting.noise_adjustment or self.get_fitting_noise_adjustment(fitting.fitting_type),
                    'position': getattr(fitting, 'position_on_segment', 0.0) or 0.0
                }
                segment_data['fittings'].append(fitting_data)
        except Exception:
            pass

        # Derive fitting type
        fitting_types = [f.get('fitting_type', '') for f in segment_data['fittings']]
        inferred_type = None
        specific_type = None
        for ft in fitting_types:
            lower_ft = (ft or '').lower()
            if not specific_type and lower_ft:
                specific_type = lower_ft
            if lower_ft.startswith('elbow'):
                inferred_type = 'elbow'
            if 'tee' in lower_ft or 'junction' in lower_ft:
                inferred_type = inferred_type or 'junction'
        
        if specific_type:
            segment_data['fitting_type'] = specific_type
        elif inferred_type:
            segment_data['fitting_type'] = inferred_type
        
        return segment_data

    def find_matching_mechanical_unit(self, component: 'HVACComponent', project_id: int) -> Optional['MechanicalUnit']:
        """Find mechanical unit that matches drawn component
        
        Tries multiple matching strategies:
        1. Exact name match first
        2. Type and capacity matching  
        3. Type matching with fuzzy name similarity
        
        Args:
            component: HVACComponent to match
            project_id: Project ID to search within
            
        Returns:
            Matching MechanicalUnit or None
        """
        from models.database import get_hvac_session
        from models.mechanical import MechanicalUnit
        import os
        
        debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
        
        with get_hvac_session() as session:
            # Try exact name match first
            if hasattr(component, 'name') and component.name:
                unit = session.query(MechanicalUnit).filter(
                    MechanicalUnit.project_id == project_id,
                    MechanicalUnit.name.ilike(component.name)  # Case insensitive
                ).first()
                
                if unit:
                    if debug_enabled:
                        print(f"DEBUG: Found exact name match: Component '{component.name}' -> Unit '{unit.name}'")
                    return unit
            
            # Try type + capacity matching for source components
            if hasattr(component, 'component_type') and component.component_type:
                # Map component types to mechanical unit types
                type_mappings = {
                    'ahu': ['AHU', 'Air Handling Unit'],
                    'rtu': ['RTU', 'Rooftop Unit'],
                    'ef': ['EF', 'Exhaust Fan'], 
                    'sf': ['SF', 'Supply Fan'],
                    'vav': ['VAV', 'Variable Air Volume'],
                    'fan': ['EF', 'SF', 'Fan'],
                    'air_handler': ['AHU', 'Air Handling Unit']
                }
                
                possible_types = type_mappings.get(component.component_type.lower(), [component.component_type.upper()])
                
                for unit_type in possible_types:
                    units = session.query(MechanicalUnit).filter(
                        MechanicalUnit.project_id == project_id,
                        MechanicalUnit.unit_type.ilike(f'%{unit_type}%')
                    ).all()
                    
                    if units:
                        if debug_enabled:
                            print(f"DEBUG: Found {len(units)} units of type '{unit_type}' for component type '{component.component_type}'")
                        
                        # If only one unit of this type, use it
                        if len(units) == 1:
                            if debug_enabled:
                                print(f"DEBUG: Single unit match: Component '{component.component_type}' -> Unit '{units[0].name}'")
                            return units[0]
                        
                        # If multiple units, try to match by name similarity
                        if hasattr(component, 'name') and component.name:
                            for unit in units:
                                # Simple fuzzy matching - check if component name contains unit identifier
                                component_name = str(component.name).upper()
                                unit_name = str(unit.name).upper()
                                
                                # Extract numbers from names for matching
                                import re
                                comp_numbers = re.findall(r'\d+', component_name)
                                unit_numbers = re.findall(r'\d+', unit_name)
                                
                                if comp_numbers and unit_numbers and comp_numbers[0] == unit_numbers[0]:
                                    if debug_enabled:
                                        print(f"DEBUG: Number-based match: Component '{component.name}' -> Unit '{unit.name}'")
                                    return unit
                                
                                # Check if unit name is contained in component name or vice versa
                                if unit_name in component_name or component_name in unit_name:
                                    if debug_enabled:
                                        print(f"DEBUG: Name similarity match: Component '{component.name}' -> Unit '{unit.name}'")
                                    return unit
                        
                        # Fallback: return first unit of matching type
                        if debug_enabled:
                            print(f"DEBUG: Fallback match: Component '{component.component_type}' -> First unit '{units[0].name}'")
                        return units[0]
            
            if debug_enabled:
                print(f"DEBUG: No mechanical unit match found for component '{getattr(component, 'name', 'unnamed')}' type '{getattr(component, 'component_type', 'unknown')}'")
            
            return None

    def order_segments_for_path(self, segments: List[HVACSegment], preferred_source_id: Optional[int] = None) -> List[HVACSegment]:
        """Unified segment ordering used by all components
        
        Orders segments by walking the chain from source to terminal.
        - If a preferred source component id is provided and exists in the chain, start from there.
        - Otherwise, start from a component that appears as a 'from' but never as a 'to'.
        - Fall back to existing segment_order if traversal fails.
        
        This is the single source of truth for segment ordering across the application.
        """
        import os
        
        try:
            if not segments:
                return []

            # Debug logging for segment ordering decisions
            debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
            if debug_enabled:
                print(f"DEBUG: Starting segment ordering for {len(segments)} segments")
                print(f"DEBUG: Preferred source component ID: {preferred_source_id}")
                for i, seg in enumerate(segments):
                    seg_id = getattr(seg, 'id', f'stub_{i}')
                    from_id = getattr(seg, 'from_component_id', None)
                    to_id = getattr(seg, 'to_component_id', None)
                    order = getattr(seg, 'segment_order', 0)
                    print(f"DEBUG: Segment {seg_id}: {from_id} -> {to_id} (order: {order})")

            # Index mappings
            from_map = {}
            to_set = set()
            for seg in segments:
                fcid = getattr(seg, 'from_component_id', None)
                tcid = getattr(seg, 'to_component_id', None)
                if fcid is not None:
                    # Prefer the first observed mapping for simple paths
                    if fcid not in from_map:
                        from_map[fcid] = seg
                if tcid is not None:
                    to_set.add(tcid)

            # Determine start component
            start_comp_id = None
            if preferred_source_id and preferred_source_id in from_map:
                start_comp_id = preferred_source_id
                if debug_enabled:
                    print(f"DEBUG: Using preferred source component: {start_comp_id}")
            else:
                # A 'from' that is never a 'to' is a likely source
                candidates = [fcid for fcid in from_map.keys() if fcid not in to_set]
                if candidates:
                    start_comp_id = candidates[0]
                    if debug_enabled:
                        print(f"DEBUG: Found source candidates: {candidates}, using: {start_comp_id}")
                else:
                    # Fallback: choose the lowest segment_order's from_component
                    try:
                        first_seg = sorted(segments, key=lambda s: getattr(s, 'segment_order', 0))[0]
                        start_comp_id = getattr(first_seg, 'from_component_id', None)
                        if debug_enabled:
                            print(f"DEBUG: Using fallback source from first segment: {start_comp_id}")
                    except Exception:
                        start_comp_id = None
                        if debug_enabled:
                            print("DEBUG: Could not determine source component")

            # Traverse chain
            ordered: List[HVACSegment] = []
            visited = set()
            current = start_comp_id
            # Limit iterations to avoid infinite loops
            max_iters = len(segments) + 2
            iters = 0
            while current is not None and iters < max_iters:
                iters += 1
                seg = from_map.get(current)
                if seg is None:
                    if debug_enabled:
                        print(f"DEBUG: No segment found from component {current}, stopping traversal")
                    break
                seg_id = getattr(seg, 'id', f'stub_{len(ordered)}')
                if seg_id in visited:
                    # Loop detected
                    if debug_enabled:
                        print(f"DEBUG: Loop detected at segment {seg_id}, stopping traversal")
                    break
                ordered.append(seg)
                visited.add(seg_id)
                current = getattr(seg, 'to_component_id', None)
                if debug_enabled:
                    print(f"DEBUG: Added segment {seg_id} to position {len(ordered)}, next component: {current}")

            # If traversal did not include all segments, append remaining by existing order
            if len(ordered) < len(segments):
                remaining = [s for s in sorted(segments, key=lambda s: getattr(s, 'segment_order', 0)) if getattr(s, 'id', id(s)) not in visited]
                ordered.extend(remaining)
                if debug_enabled:
                    print(f"DEBUG: Added {len(remaining)} remaining segments by stored order")

            # Debug final ordering
            if debug_enabled:
                print("DEBUG: Final segment ordering:")
                for i, seg in enumerate(ordered):
                    seg_id = getattr(seg, 'id', f'stub_{i}')
                    from_id = getattr(seg, 'from_component_id', None)
                    to_id = getattr(seg, 'to_component_id', None)
                    print(f"DEBUG: Position {i+1}: Segment {seg_id}: {from_id} -> {to_id}")

            return ordered if ordered else list(sorted(segments, key=lambda s: getattr(s, 'segment_order', 0)))
        except Exception as e:
            if os.environ.get('HVAC_DEBUG_EXPORT'):
                print(f"DEBUG: Segment ordering failed with error: {e}, falling back to stored order")
            return list(sorted(segments, key=lambda s: getattr(s, 'segment_order', 0)))
    
    def _order_segments_by_connectivity(self, segments: List[HVACSegment], preferred_source_component_id: Optional[int] = None) -> List[HVACSegment]:
        """Legacy method - now delegates to unified ordering method"""
        return self.order_segments_for_path(segments, preferred_source_component_id)
    
    def get_component_noise_level(self, component_type: str) -> float:
        """Get standard noise level for component type"""
        return STANDARD_COMPONENTS.get(component_type, {}).get('noise_level', 50.0)
    
    def get_fitting_noise_adjustment(self, fitting_type: str) -> float:
        """Get standard noise adjustment for fitting type"""
        return STANDARD_FITTINGS.get(fitting_type, {}).get('noise_adjustment', 0.0)
    
    def _export_enhanced_debug_data(self, hvac_path, path_data):
        """Export enhanced debug data with all phases information"""
        try:
            import json
            from datetime import datetime
            
            # Ensure debug export directory exists
            debug_dir = os.path.expanduser("~/Documents/drawings_to_acoustics_processor/debug_data/debug_exports")
            os.makedirs(debug_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path_name = getattr(hvac_path, 'name', 'unknown_path').replace(' ', '_').replace('/', '_')
            filename = f"hvac_debug_{path_name}_{timestamp}.json"
            filepath = os.path.join(debug_dir, filename)
            
            # Gather all debug information
            debug_data = {
                'metadata': {
                    'export_timestamp': timestamp,
                    'path_id': getattr(hvac_path, 'id', None),
                    'path_name': getattr(hvac_path, 'name', 'unknown'),
                    'project_id': self.project_id,
                    'debug_version': '2.0_enhanced'
                },
                'path_info': {
                    'name': getattr(hvac_path, 'name', 'unknown'),
                    'description': getattr(hvac_path, 'description', ''),
                    'path_type': getattr(hvac_path, 'path_type', 'unknown'),
                    'primary_source_id': getattr(hvac_path, 'primary_source_id', None),
                    'target_space_id': getattr(hvac_path, 'target_space_id', None)
                },
                'segment_ordering': {
                    'total_segments': len(getattr(hvac_path, 'segments', [])),
                    'segments': []
                },
                'mechanical_unit_integration': {},
                'validation_results': {},
                'path_data': path_data
            }
            
            # Enhanced segment ordering information
            segments = getattr(hvac_path, 'segments', [])
            for i, segment in enumerate(segments):
                seg_info = {
                    'position': i + 1,
                    'segment_id': getattr(segment, 'id', None),
                    'segment_order': getattr(segment, 'segment_order', None),
                    'from_component_id': getattr(segment, 'from_component_id', None),
                    'to_component_id': getattr(segment, 'to_component_id', None),
                    'length': getattr(segment, 'length', None),
                    'duct_dimensions': {
                        'width': getattr(segment, 'duct_width', None),
                        'height': getattr(segment, 'duct_height', None),
                        'shape': getattr(segment, 'duct_shape', None)
                    }
                }
                debug_data['segment_ordering']['segments'].append(seg_info)
            
            # Mechanical unit integration information
            if getattr(hvac_path, 'primary_source_id', None):
                try:
                    from models.database import get_hvac_session
                    from models.mechanical import MechanicalUnit
                    
                    with get_hvac_session() as session:
                        unit = session.query(MechanicalUnit).filter(
                            MechanicalUnit.id == hvac_path.primary_source_id
                        ).first()
                        
                        if unit:
                            debug_data['mechanical_unit_integration'] = {
                                'linked_unit_id': unit.id,
                                'linked_unit_name': unit.name,
                                'linked_unit_type': unit.unit_type,
                                'airflow_cfm': unit.airflow_cfm,
                                'external_static_inwg': unit.external_static_inwg,
                                'power_kw': unit.power_kw
                            }
                
                except Exception as e:
                    debug_data['mechanical_unit_integration'] = {'error': str(e)}
            
            # Validation results
            if path_data and path_data.get('validation_result'):
                validation = path_data['validation_result']
                debug_data['validation_results'] = {
                    'is_valid': validation.is_valid,
                    'errors': validation.errors,
                    'warnings': validation.warnings,
                    'info': validation.info
                }
            
            # Database session lifecycle info
            debug_data['session_info'] = {
                'session_management': 'unified_context_manager',
                'transaction_safety': 'automatic_rollback_on_error'
            }
            
            # Export to JSON
            with open(filepath, 'w') as f:
                json.dump(debug_data, f, indent=2, default=str)
            
            print(f"DEBUG: Enhanced debug data exported to: {filepath}")
            
        except Exception as e:
            print(f"DEBUG: Enhanced debug export failed: {e}")
    
    def generate_debug_report(self, path_id: int) -> Dict[str, Any]:
        """Generate comprehensive debug report for a path"""
        from datetime import datetime
        
        report = {
            'path_id': path_id,
            'timestamp': datetime.now().isoformat(),
            'issues_detected': [],
            'recommendations': [],
            'system_health': {}
        }
        
        try:
            from src.models.database import get_hvac_session
            from src.calculations.hvac_validation import HVACValidationFramework
            
            with get_hvac_session() as session:
                path = session.query(HVACPath).filter(HVACPath.id == path_id).first()
                
                if not path:
                    report['issues_detected'].append("Path not found in database")
                    return report
                
                # Run comprehensive validation
                validator = HVACValidationFramework(self.project_id)
                validation = validator.validate_path(path)
                
                report['validation_summary'] = {
                    'is_valid': validation.is_valid,
                    'error_count': len(validation.errors),
                    'warning_count': len(validation.warnings),
                    'info_count': len(validation.info)
                }
                
                # Detect common issues
                if not validation.is_valid:
                    report['issues_detected'].extend(validation.errors)
                
                if validation.warnings:
                    report['issues_detected'].extend(validation.warnings)
                
                # Check segment connectivity
                segments = path.segments
                if segments:
                    if len(segments) > 10:
                        report['recommendations'].append("Path has many segments - consider simplifying")
                    
                    # Check for missing connections
                    disconnected = 0
                    for seg in segments:
                        if not getattr(seg, 'from_component_id', None) or not getattr(seg, 'to_component_id', None):
                            disconnected += 1
                    
                    if disconnected > 0:
                        report['issues_detected'].append(f"{disconnected} segments have missing connections")
                
                # Check mechanical unit integration
                if path.primary_source_id:
                    report['system_health']['mechanical_unit_linked'] = True
                else:
                    report['recommendations'].append("Consider linking to a mechanical unit for more accurate calculations")
                
                report['system_health']['total_segments'] = len(segments) if segments else 0
                report['system_health']['has_validation_framework'] = True
                report['system_health']['unified_segment_ordering'] = True
                report['system_health']['session_management'] = 'enhanced'
                
        except Exception as e:
            report['issues_detected'].append(f"Debug report generation failed: {e}")
        
        return report
    
    # --- Debug export helper ---
    def _debug_export_path_result(self, hvac_path: HVACPath, path_data: Dict[str, Any], calc_results: Dict[str, Any]) -> None:
        """Export per-path, per-element spectra and summary as JSON and CSV.
        Controlled by HVAC_DEBUG_EXPORT env var (1/true/yes/on)."""
        try:
            # Prepare directory
            base_dir = os.path.join(get_user_data_directory(), "debug_exports", f"project_{getattr(hvac_path, 'project_id', 'unknown')}")
            os.makedirs(base_dir, exist_ok=True)
            # Prepare filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_name = getattr(hvac_path, 'name', '') or f"path_{hvac_path.id}"
            safe_name = ''.join(ch if (ch.isalnum() or ch in {'-', '_'}) else '_' for ch in raw_name)
            json_path = os.path.join(base_dir, f"path_{hvac_path.id}_{safe_name}_{timestamp}.json")
            csv_path = os.path.join(base_dir, f"path_{hvac_path.id}_{safe_name}_{timestamp}.csv")

            # Frequency bands (engine standard)
            bands = [63, 125, 250, 500, 1000, 2000, 4000, 8000]

            # Build JSON payload
            payload: Dict[str, Any] = {
                'project_id': getattr(hvac_path, 'project_id', None),
                'path_id': hvac_path.id,
                'path_name': raw_name,
                'timestamp': timestamp,
                'frequency_bands_hz': bands,
                'source': {
                    'noise_dba': calc_results.get('source_noise'),
                    'octave_band_levels': (path_data.get('source_component') or {}).get('octave_band_levels')
                },
                'terminal': {
                    'noise_dba': calc_results.get('terminal_noise'),
                    'octave_band_spectrum': calc_results.get('octave_band_spectrum')
                },
                'nc_rating': calc_results.get('nc_rating'),
                'total_attenuation_dba': calc_results.get('total_attenuation_dba', calc_results.get('total_attenuation')),
                'elements': []
            }

            segs: List[Dict[str, Any]] = path_data.get('segments', []) or []
            elements: List[Dict[str, Any]] = calc_results.get('path_segments', []) or []
            for elem in elements:
                order = int(elem.get('element_order', -1))
                etype = elem.get('element_type')
                geometry: Optional[Dict[str, Any]] = None
                # Map non-source, non-terminal elements to segment geometry by order-1
                if etype != 'source' and order >= 1 and order - 1 < len(segs):
                    s = segs[order - 1]
                    geometry = {
                        'length_ft': float(s.get('length', 0.0) or 0.0),
                        'duct_shape': s.get('duct_shape'),
                        'duct_type': s.get('duct_type'),
                        'width_in': float(s.get('duct_width', 0.0) or 0.0),
                        'height_in': float(s.get('duct_height', 0.0) or 0.0),
                        'diameter_in': float(s.get('diameter', 0.0) or 0.0),
                        'lining_in': float(s.get('lining_thickness', 0.0) or 0.0),
                    }
                payload['elements'].append({
                    'element_order': order,
                    'element_type': etype,
                    'element_id': elem.get('element_id'),
                    'noise_before_dba': elem.get('noise_before'),
                    'noise_after_dba': elem.get('noise_after_dba', elem.get('noise_after')),
                    'nc_rating': elem.get('nc_rating'),
                    'attenuation_dba': elem.get('attenuation_dba'),
                    'generated_dba': elem.get('generated_dba'),
                    'attenuation_spectrum': elem.get('attenuation_spectrum'),
                    'generated_spectrum': elem.get('generated_spectrum'),
                    'noise_after_spectrum': elem.get('noise_after_spectrum'),
                    'geometry': geometry,
                })

            # Write JSON
            with open(json_path, 'w', encoding='utf-8') as jf:
                _json.dump(payload, jf, indent=2)

            # Write CSV (per-element row with band columns)
            headers = [
                'project_id', 'path_id', 'path_name', 'timestamp',
                'element_order', 'element_type', 'element_id',
                'noise_before_dba', 'noise_after_dba', 'attenuation_dba', 'generated_dba', 'nc_rating',
                'length_ft', 'duct_shape', 'duct_type', 'width_in', 'height_in', 'diameter_in', 'lining_in'
            ]
            # Add band-specific columns
            headers += [f"after_{b}" for b in bands]
            headers += [f"att_{b}" for b in bands]
            headers += [f"gen_{b}" for b in bands]

            with open(csv_path, 'w', newline='', encoding='utf-8') as cf:
                writer = _csv.DictWriter(cf, fieldnames=headers)
                writer.writeheader()
                for elem in payload['elements']:
                    row = {
                        'project_id': payload['project_id'],
                        'path_id': payload['path_id'],
                        'path_name': payload['path_name'],
                        'timestamp': payload['timestamp'],
                        'element_order': elem.get('element_order'),
                        'element_type': elem.get('element_type'),
                        'element_id': elem.get('element_id'),
                        'noise_before_dba': elem.get('noise_before_dba'),
                        'noise_after_dba': elem.get('noise_after_dba'),
                        'attenuation_dba': elem.get('attenuation_dba'),
                        'generated_dba': elem.get('generated_dba'),
                        'nc_rating': elem.get('nc_rating'),
                        'length_ft': (elem.get('geometry') or {}).get('length_ft'),
                        'duct_shape': (elem.get('geometry') or {}).get('duct_shape'),
                        'duct_type': (elem.get('geometry') or {}).get('duct_type'),
                        'width_in': (elem.get('geometry') or {}).get('width_in'),
                        'height_in': (elem.get('geometry') or {}).get('height_in'),
                        'diameter_in': (elem.get('geometry') or {}).get('diameter_in'),
                        'lining_in': (elem.get('geometry') or {}).get('lining_in'),
                    }
                    after = elem.get('noise_after_spectrum') or []
                    att = elem.get('attenuation_spectrum') or []
                    gen = elem.get('generated_spectrum') or []
                    # Normalize to 8 values
                    def _pad(x):
                        if not isinstance(x, list):
                            return [0.0] * 8
                        return (list(x) + [0.0] * 8)[:8]
                    after8 = _pad(after)
                    att8 = _pad(att)
                    gen8 = _pad(gen)
                    for i, b in enumerate(bands):
                        row[f"after_{b}"] = after8[i]
                        row[f"att_{b}"] = att8[i]
                        row[f"gen_{b}"] = gen8[i]
                    writer.writerow(row)
        except Exception as ex:
            # Don't break main flow on debug export failures
            print(f"DEBUG_EXPORT: Exception during export for path {getattr(hvac_path, 'id', '?')}: {ex}")
    
    def update_segment_properties(self, segment_id: int, properties: Dict) -> bool:
        """
        Update HVAC segment properties
        
        Args:
            segment_id: Segment ID
            properties: Dictionary of properties to update
            
        Returns:
            True if successful
        """
        session = None
        try:
            session = get_session()
            segment = session.query(HVACSegment).filter(HVACSegment.id == segment_id).first()
            
            if not segment:
                session.close()
                return False
            
            # Update properties
            for key, value in properties.items():
                if hasattr(segment, key):
                    setattr(segment, key, value)
            
            session.commit()
            
            # Recalculate path noise
            self.calculate_path_noise(segment.hvac_path_id)
            
            session.close()
            return True
            
        except Exception as e:
            if session is not None:
                try:
                    session.rollback()
                except Exception:
                    pass
                try:
                    session.close()
                except Exception:
                    pass
            print(f"Error updating segment properties: {e}")
            return False
    
    def add_segment_fitting(self, segment_id: int, fitting_type: str, position: float = 0.0) -> bool:
        """
        Add fitting to HVAC segment
        
        Args:
            segment_id: Segment ID
            fitting_type: Type of fitting
            position: Position on segment (feet from start)
            
        Returns:
            True if successful
        """
        session = None
        try:
            session = get_session()
            
            fitting = SegmentFitting(
                segment_id=segment_id,
                fitting_type=fitting_type,
                position_on_segment=position,
                noise_adjustment=self.get_fitting_noise_adjustment(fitting_type)
            )
            
            session.add(fitting)
            session.commit()
            
            # Recalculate path noise
            segment = session.query(HVACSegment).filter(HVACSegment.id == segment_id).first()
            if segment:
                self.calculate_path_noise(segment.hvac_path_id)
            
            session.close()
            return True
            
        except Exception as e:
            if session is not None:
                try:
                    session.rollback()
                except Exception:
                    pass
                try:
                    session.close()
                except Exception:
                    pass
            print(f"Error adding segment fitting: {e}")
            return False
    
    def get_path_summary(self, project_id: int) -> Dict:
        """
        Get summary of all HVAC paths in project
        
        Args:
            project_id: Project ID
            
        Returns:
            Summary dictionary
        """
        session = None
        try:
            session = get_session()
            
            hvac_paths = session.query(HVACPath).filter(
                HVACPath.project_id == project_id
            ).all()
            
            summary = {
                'total_paths': len(hvac_paths),
                'calculated_paths': 0,
                'avg_noise_level': 0.0,
                'avg_nc_rating': 0.0,
                'paths_by_type': {},
                'paths_over_nc45': 0
            }
            
            total_noise = 0.0
            total_nc = 0.0
            
            for path in hvac_paths:
                if path.calculated_noise is not None:
                    summary['calculated_paths'] += 1
                    total_noise += path.calculated_noise
                    
                    if path.calculated_nc is not None:
                        total_nc += path.calculated_nc
                        if path.calculated_nc > 45:
                            summary['paths_over_nc45'] += 1
                
                # Count by type
                path_type = path.path_type or 'unknown'
                summary['paths_by_type'][path_type] = summary['paths_by_type'].get(path_type, 0) + 1
            
            if summary['calculated_paths'] > 0:
                summary['avg_noise_level'] = total_noise / summary['calculated_paths']
                summary['avg_nc_rating'] = total_nc / summary['calculated_paths']
            
            session.close()
            return summary
            
        except Exception as e:
            try:
                if session is not None:
                    session.close()
            except Exception:
                pass
            print(f"Error getting path summary: {e}")
            return {
                'total_paths': 0,
                'calculated_paths': 0,
                'avg_noise_level': 0.0,
                'avg_nc_rating': 0.0,
                'paths_by_type': {},
                'paths_over_nc45': 0
            }
    
    def export_path_results(self, project_id: int) -> List[Dict]:
        """
        Export HVAC path results for Excel/reporting
        
        Args:
            project_id: Project ID
            
        Returns:
            List of path result dictionaries
        """
        results = []
        
        session = None
        try:
            session = get_session()
            
            hvac_paths = session.query(HVACPath).filter(
                HVACPath.project_id == project_id
            ).all()
            
            for path in hvac_paths:
                result = {
                    'Path Name': path.name,
                    'Path Type': path.path_type or 'supply',
                    'Description': path.description or '',
                    'Calculated Noise (dB)': path.calculated_noise or 0,
                    'NC Rating': path.calculated_nc or 0,
                    'Segment Count': len(path.segments),
                    'Total Length (ft)': sum(seg.length or 0 for seg in path.segments),
                    'Target Space': path.target_space.name if path.target_space else ''
                }
                results.append(result)
            
            session.close()
            
        except Exception as e:
            try:
                if session is not None:
                    session.close()
            except Exception:
                pass
            print(f"Error exporting path results: {e}")
        
        return results