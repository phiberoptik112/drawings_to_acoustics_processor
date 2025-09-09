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
from .hvac_noise_engine import HVACNoiseEngine
from .debug_logger import debug_logger
from .result_types import CalculationResult, PathCreationResult, OperationResult
from .hvac_constants import (
    DEFAULT_DUCT_WIDTH_IN, DEFAULT_DUCT_HEIGHT_IN, DEFAULT_FLOW_VELOCITY_FPM,
    NUM_OCTAVE_BANDS, FREQUENCY_BAND_LABELS, DEFAULT_SPECTRUM_LEVELS,
    DEFAULT_NC_RATING, MAX_PATH_ELEMENTS, INCHES_PER_FOOT,
    DEFAULT_CFM_VALUES, DEFAULT_CFM_FALLBACK, get_default_cfm_for_component,
    DEFAULT_COMPONENT_NOISE_LEVELS
)
# Debug export imports
import os
from datetime import datetime
import json as _json
import csv as _csv
from utils import get_user_data_directory


def _env_truthy(value: Optional[str]) -> bool:
    """Interpret common truthy strings for environment flags."""
    try:
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    except Exception:
        return False

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
        self.noise_calculator = HVACNoiseEngine()
        # Debug logging is now handled by centralized logger
        self.debug_logger = debug_logger
        # Unified flag used throughout this class; avoids AttributeError in debug guards
        import os as _os
        self.debug_export_enabled = _env_truthy(_os.environ.get('HVAC_DEBUG_EXPORT'))
    
    def create_hvac_path_from_drawing(self, project_id: int, drawing_data: Dict) -> CalculationResult[HVACPath]:
        """
        Create HVAC path from drawing elements (components and segments)
        
        Args:
            project_id: Project ID
            drawing_data: Dictionary containing components and segments from drawing
            
        Returns:
            CalculationResult containing HVACPath on success or error details on failure
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
                    component_type = comp_data.get('component_type', 'unknown')
                    
                    hvac_comp = HVACComponent(
                        project_id=project_id,
                        drawing_id=comp_data.get('drawing_id', 0),
                        name=f"{component_type.upper()}-{len(db_components)+1}",
                        component_type=component_type,
                        x_position=comp_data.get('x', 0),
                        y_position=comp_data.get('y', 0),
                        # Provide a sensible default A-weighted level so a path can be calculated
                        # even when mechanical schedules are not linked yet.
                        noise_level=comp_data.get('noise_level')
                                    or DEFAULT_COMPONENT_NOISE_LEVELS.get(component_type.lower(), 50.0),
                        cfm=comp_data.get('cfm') or get_default_cfm_for_component(component_type)
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
                
                # Try to find mechanical unit for primary source (for enrichment only)
                primary_source_unit_id = None
                try:
                    matched_unit = self.find_matching_mechanical_unit(source_comp, project_id)
                    if matched_unit:
                        primary_source_unit_id = matched_unit.id
                        import os
                        if os.environ.get('HVAC_DEBUG_EXPORT'):
                            print(f"DEBUG: Matched primary source component '{source_comp.name}' to mechanical unit '{matched_unit.name}' for spectrum enrichment")
                except Exception as e:
                    import os
                    if os.environ.get('HVAC_DEBUG_EXPORT'):
                        print(f"DEBUG: Could not match primary source to mechanical unit: {e}")
                
                hvac_path = HVACPath(
                    project_id=project_id,
                    name=f"Path: {source_comp.component_type.upper()} to {terminal_comp.component_type.upper()}",
                    description=f"HVAC path from {source_comp.name} to {terminal_comp.name}",
                    path_type='supply',
                    # Store the HVACComponent as the primary source per schema
                    primary_source_id=source_comp.id
                )
                session.add(hvac_path)
                session.flush()  # Get ID
                
                # Create segments using actual connections from drawing
                created_segments: List[HVACSegment] = []
                import os
                debug_enabled = os.environ.get('HVAC_DEBUG_EXPORT')
                if debug_enabled:
                    print(f"DEBUG_PATH: Creating {len(segments)} segments from drawing data:")
                for i, seg_data in enumerate(segments):
                    if debug_enabled:
                        print(f"DEBUG_PATH: Segment {i} data keys: {list(seg_data.keys())}")
                        print(f"DEBUG_PATH: Segment {i} length_real: {seg_data.get('length_real', 'MISSING')}")
                        print(f"DEBUG_PATH: Segment {i} duct_width: {seg_data.get('duct_width', 'MISSING')}")
                        print(f"DEBUG_PATH: Segment {i} duct_height: {seg_data.get('duct_height', 'MISSING')}")
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
                    
                    # Only create segment if BOTH endpoints are resolved to satisfy NOT NULL FKs
                    if from_comp_id is not None and to_comp_id is not None:
                        # Get CFM from source component, fallback to defaults
                        from_comp = next((c for c in db_components.values() if c.id == from_comp_id), None)
                        segment_cfm = DEFAULT_CFM_FALLBACK
                        cfm_source = "fallback"
                        
                        if from_comp and hasattr(from_comp, 'cfm') and from_comp.cfm:
                            segment_cfm = from_comp.cfm
                            cfm_source = "component_cfm"
                        elif from_comp and hasattr(from_comp, 'component_type'):
                            segment_cfm = get_default_cfm_for_component(from_comp.component_type)
                            cfm_source = f"default_for_{from_comp.component_type}"
                        
                        # Debug CFM assignment
                        print(f"DEBUG_CFM: Segment {i+1} CFM assignment:")
                        print(f"DEBUG_CFM:   From component: {from_comp.component_type if from_comp else 'None'}")
                        print(f"DEBUG_CFM:   Component CFM: {getattr(from_comp, 'cfm', 'None') if from_comp else 'None'}")
                        print(f"DEBUG_CFM:   CFM source: {cfm_source}")
                        print(f"DEBUG_CFM:   Final segment CFM: {segment_cfm}")
                            
                        hvac_segment = HVACSegment(
                            hvac_path_id=hvac_path.id,
                            from_component_id=from_comp_id,
                            to_component_id=to_comp_id,
                            length=seg_data.get('length_real', 0),
                            segment_order=i+1,
                            # Persist duct dimensions from drawing if present; otherwise defaults
                            duct_width=seg_data.get('duct_width') or DEFAULT_DUCT_WIDTH_IN,
                            duct_height=seg_data.get('duct_height') or DEFAULT_DUCT_HEIGHT_IN,
                            duct_shape='rectangular',
                            duct_type='sheet_metal',
                            flow_rate=segment_cfm
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
                        if from_comp_id is not None and to_comp_id is not None:
                            # Get CFM from fallback logic too
                            from_comp = next((c for c in db_components.values() if c.id == from_comp_id), None)
                            segment_cfm = DEFAULT_CFM_FALLBACK
                            if from_comp and hasattr(from_comp, 'cfm') and from_comp.cfm:
                                segment_cfm = from_comp.cfm
                            elif from_comp and hasattr(from_comp, 'component_type'):
                                segment_cfm = get_default_cfm_for_component(from_comp.component_type)
                                
                            hvac_segment = HVACSegment(
                                hvac_path_id=hvac_path.id,
                                from_component_id=from_comp_id,
                                to_component_id=to_comp_id,
                                length=seg_data.get('length_real', 0),
                                segment_order=i+1,
                                duct_width=seg_data.get('duct_width') or DEFAULT_DUCT_WIDTH_IN,
                                duct_height=seg_data.get('duct_height') or DEFAULT_DUCT_HEIGHT_IN,
                                duct_shape='rectangular',
                                duct_type='sheet_metal',
                                flow_rate=segment_cfm
                            )
                            session.add(hvac_segment)
                            created_segments.append(hvac_segment)
                        else:
                            if self.debug_export_enabled:
                                print(f"DEBUG: Skipping segment {i} creation - endpoints not both resolved (from={from_comp_id}, to={to_comp_id})")
                
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
                
                return CalculationResult.success(
                    hvac_path,
                    metadata={
                        'components_created': len(db_components),
                        'segments_created': len(created_segments),
                        'mechanical_unit_linked': primary_source_unit_id is not None
                    }
                )
            
        except Exception as e:
            self.debug_logger.error('PathCalculator', 'Error creating HVAC path', error=e)
            return CalculationResult.error(f"Failed to create HVAC path: {str(e)}")
    
    def calculate_path_noise(self, path_id: int, debug: bool = False, origin: str = "user") -> PathAnalysisResult:
        """
        Calculate noise for a specific HVAC path with validation
        
        Args:
            path_id: HVAC path ID
            
        Returns:
            PathAnalysisResult with calculation details
        """
        from src.calculations.hvac_validation import HVACValidationFramework
        # Delineated banner for calculator start
        try:
            if getattr(self, 'debug_export_enabled', False):
                print(f"\n===== [PATH CALCULATOR] START | origin={origin} | path_id={path_id} =====")
        except Exception:
            pass
        
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
            # Thread origin via environment for downstream builders
            try:
                os.environ['HVAC_CALC_ORIGIN'] = origin or 'user'
            except Exception:
                pass
            try:
                path_data = self.build_path_data_from_db(hvac_path)
            finally:
                try:
                    del os.environ['HVAC_CALC_ORIGIN']
                except Exception:
                    pass
            
            if not path_data:
                raise ValueError("Could not build path data from database")
            
            # Perform calculation with enhanced debugging
            if self.debug_export_enabled:
                print(f"DEBUG: Pre-calculation path_data structure:")
                print(f"DEBUG: - Source component: {path_data.get('source_component', {})[:100] if isinstance(path_data.get('source_component'), dict) else path_data.get('source_component')}")
                print(f"DEBUG: - Terminal component: {path_data.get('terminal_component', {})}")
                print(f"DEBUG: - Segments count: {len(path_data.get('segments', []))}")
                for i, seg in enumerate(path_data.get('segments', [])):
                    print(f"DEBUG: - Segment {i+1}: length={seg.get('length')}, flow_rate={seg.get('flow_rate')}, duct={seg.get('duct_width')}x{seg.get('duct_height')}")
                
            calc_results = self.noise_calculator.calculate_hvac_path_noise(path_data, debug=debug, origin=origin, path_id=str(path_id))
            
            if self.debug_export_enabled:
                print(f"DEBUG: Post-calculation results:")
                print(f"DEBUG: - Source noise: {calc_results.get('source_noise')} dB(A)")
                print(f"DEBUG: - Terminal noise: {calc_results.get('terminal_noise')} dB(A)")
                print(f"DEBUG: - Calculation valid: {calc_results.get('calculation_valid')}")
                print(f"DEBUG: - Error: {calc_results.get('error')}")
                print(f"DEBUG: - Path segments count: {len(calc_results.get('path_segments', []))}")
                if calc_results.get('warnings'):
                    print(f"DEBUG: - Warnings: {calc_results.get('warnings')}")
            
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
            if self.debug_export_enabled:
                print(f"DEBUG: Creating PathAnalysisResult with:")
                print(f"DEBUG: - calc_results['calculation_valid']: {calc_results['calculation_valid']}")
                print(f"DEBUG: - calc_results['source_noise']: {calc_results['source_noise']}")
                print(f"DEBUG: - calc_results['terminal_noise']: {calc_results['terminal_noise']}")
            
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
            try:
                if getattr(self, 'debug_export_enabled', False):
                    print(f"===== [PATH CALCULATOR] END   | origin={origin} | valid={result.calculation_valid} | nc={result.nc_rating} | terminal={result.terminal_noise:.1f} dB(A) =====\n")
            except Exception:
                pass
            return result
            
        except Exception as e:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
            end_result = PathAnalysisResult(
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
            try:
                if getattr(self, 'debug_export_enabled', False):
                    print(f"===== [PATH CALCULATOR] END   | origin={origin} | valid={end_result.calculation_valid} | error=1 =====\n")
            except Exception:
                pass
            return end_result
    
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
                # Mark as background-origin for batch calculations
                os.environ['HVAC_CALC_ORIGIN'] = 'background'
                try:
                    result = self.calculate_path_noise(hvac_path.id, origin='background')
                finally:
                    try:
                        del os.environ['HVAC_CALC_ORIGIN']
                    except Exception:
                        pass
                results.append(result)
            
            session.close()
            
        except Exception as e:
            print(f"Error calculating project paths: {e}")
        
        return results
    
    def build_path_data_from_db(self, hvac_path: HVACPath) -> CalculationResult[Dict]:
        """
        Build path data structure from database HVAC path
        
        Args:
            hvac_path: HVACPath database object
            
        Returns:
            Path data dictionary for noise calculation
        """
        print("-=-=--=-=-=-=-=--=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
        print(f"DEBUG_ENTRY: build_path_data_from_db called")
        print("-=-=--=-=-=-=-=--=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
        print(f"DEBUG_ENTRY: hvac_path type: {type(hvac_path)}")
        print(f"DEBUG_ENTRY: hvac_path id: {getattr(hvac_path, 'id', 'None')}")
        
        # Always refetch the path with eager-loaded relationships to avoid
        # lazy-loading on detached instances coming from the UI layer.
        try:
            path_id = getattr(hvac_path, 'id', None) if not isinstance(hvac_path, int) else int(hvac_path)
            if path_id is None:
                raise ValueError("HVACPath id is required to build path data")
            
            print(f"DEBUG_ENTRY: Using path_id: {path_id}")
            
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
        print(f"DEBUG_LEGACY: _build_path_data_within_session called for path {getattr(hvac_path, 'id', 'unknown')}")
        print(f"DEBUG_LEGACY: This is the OLD method - PathDataBuilder is NOT being used!")
        
        try:
            from models.mechanical import MechanicalUnit
            
            path_data = {
                'source_component': {},
                'terminal_component': {},
                'segments': []
            }
            
            segments = hvac_path.segments
            print(f"DEBUG_LEGACY: Number of segments: {len(segments) if segments else 0}")
            if not segments:
                print(f"DEBUG_LEGACY: No segments found, returning None")
                return None
            
            # Ensure segments are ordered by actual connectivity
            try:
                preferred_source_id = getattr(hvac_path, 'primary_source_id', None)
                segments = self.order_segments_for_path(list(segments), preferred_source_id)
            except Exception as e:
                if self.debug_export_enabled:
                    print(f"DEBUG: Using stored segment order; connectivity ordering failed: {e}")

            # Get source: prefer explicit HVACComponent relationship; otherwise derive from MechanicalUnit or first component
            source_comp = getattr(hvac_path, 'primary_source', None)
            
            print(f"DEBUG_SOURCE_SELECTION: Source component selection logic:")
            print(f"DEBUG_SOURCE_SELECTION:   hvac_path.primary_source: {source_comp}")
            print(f"DEBUG_SOURCE_SELECTION:   hvac_path.primary_source_id: {getattr(hvac_path, 'primary_source_id', None)}")
            print(f"DEBUG_SOURCE_SELECTION:   hvac_path.id: {getattr(hvac_path, 'id', None)}")
            print(f"DEBUG_SOURCE_SELECTION:   IMPORTANT: The configured primary source is ELBOW-1 (ID: 5)")
            print(f"DEBUG_SOURCE_SELECTION:   ELBOW-1 is a passive component - it will inherit CFM from upstream active components")
            print(f"DEBUG_SOURCE_SELECTION:   The actual CFM source should be RF 1-1 (ID: 197) - the active fan component")
            
            if source_comp is not None:
                # Enhanced debugging for source component in legacy method
                print(f"DEBUG_LEGACY_SOURCE: Source component found:")
                print(f"DEBUG_LEGACY_SOURCE:   Type: {type(source_comp)}")
                print(f"DEBUG_LEGACY_SOURCE:   ID: {getattr(source_comp, 'id', 'None')}")
                print(f"DEBUG_LEGACY_SOURCE:   Name: {getattr(source_comp, 'name', 'None')}")
                print(f"DEBUG_LEGACY_SOURCE:   Component type: {getattr(source_comp, 'component_type', 'None')}")
                print(f"DEBUG_LEGACY_SOURCE:   Noise level: {getattr(source_comp, 'noise_level', 'None')}")
                print(f"DEBUG_LEGACY_SOURCE:   CFM attribute: {getattr(source_comp, 'cfm', 'None')}")
                print(f"DEBUG_LEGACY_SOURCE:   Has CFM attr: {hasattr(source_comp, 'cfm')}")
                
                # Try to refresh the object from database
                try:
                    session.refresh(source_comp)
                    print(f"DEBUG_LEGACY_SOURCE: After refresh - CFM: {getattr(source_comp, 'cfm', 'None')}")
                except Exception as e:
                    print(f"DEBUG_LEGACY_SOURCE: Could not refresh object: {e}")
                
                # Try direct database query
                try:
                    from models.hvac import HVACComponent
                    db_comp = session.query(HVACComponent).filter(HVACComponent.id == source_comp.id).first()
                    if db_comp:
                        print(f"DEBUG_LEGACY_SOURCE: Direct DB query - CFM: {db_comp.cfm}")
                        print(f"DEBUG_LEGACY_SOURCE: Direct DB query - Component name: {db_comp.name}")
                        print(f"DEBUG_LEGACY_SOURCE: Direct DB query - Component type: {db_comp.component_type}")
                        print(f"DEBUG_LEGACY_SOURCE: Direct DB query - All CFM-related fields:")
                        print(f"DEBUG_LEGACY_SOURCE:   cfm: {db_comp.cfm}")
                        print(f"DEBUG_LEGACY_SOURCE:   airflow_cfm: {getattr(db_comp, 'airflow_cfm', 'No airflow_cfm field')}")
                        print(f"DEBUG_LEGACY_SOURCE:   flow_rate: {getattr(db_comp, 'flow_rate', 'No flow_rate field')}")
                    else:
                        print(f"DEBUG_LEGACY_SOURCE: Direct DB query - Component not found")
                except Exception as e:
                    print(f"DEBUG_LEGACY_SOURCE: Direct DB query failed: {e}")
                
                # Seed from component; attempt to enrich with Mechanical Unit spectrum by matching
                if self.debug_export_enabled:
                    try:
                        print("DEBUG: Source component present:", {
                            'id': getattr(source_comp, 'id', None),
                            'type': getattr(source_comp, 'component_type', None),
                            'noise_level': getattr(source_comp, 'noise_level', None),
                            'cfm': getattr(source_comp, 'cfm', None),  # Add CFM to debug output
                        })
                    except Exception:
                        pass
                
                # FIXED: Handle passive component CFM calculation
                source_cfm = getattr(source_comp, 'cfm', None)
                source_type = getattr(source_comp, 'component_type', '')
                
                # Check if this is a passive component that should inherit CFM from upstream
                passive_components = ['elbow', 'junction', 'tee', 'reducer', 'damper', 'silencer']
                is_passive = source_type.lower() in passive_components
                
                print(f"DEBUG_LEGACY_SOURCE: Component analysis:")
                print(f"DEBUG_LEGACY_SOURCE:   Component type: {source_type}")
                print(f"DEBUG_LEGACY_SOURCE:   Is passive component: {is_passive}")
                print(f"DEBUG_LEGACY_SOURCE:   Original CFM: {source_cfm}")
                
                if is_passive and (source_cfm is None or source_cfm == 0):
                    # For passive components, find upstream active component
                    print(f"DEBUG_LEGACY_SOURCE: Passive component detected - finding upstream active component")
                    
                    # Look for active components in the path segments
                    active_cfm = None
                    for segment in segments:
                        from_comp = getattr(segment, 'from_component', None)
                        if from_comp:
                            from_type = getattr(from_comp, 'component_type', '')
                            from_cfm = getattr(from_comp, 'cfm', None)
                            
                            # Check if this is an active component (fan, ahu, etc.)
                            active_components = ['fan', 'ahu', 'unit', 'blower', 'compressor']
                            is_active = from_type.lower() in active_components
                            
                            print(f"DEBUG_LEGACY_SOURCE:   Checking component {getattr(from_comp, 'id', 'unknown')} ({from_type}): CFM={from_cfm}, Active={is_active}")
                            
                            if is_active and from_cfm and from_cfm > 0:
                                active_cfm = from_cfm
                                print(f"DEBUG_LEGACY_SOURCE:   Found active component with CFM: {active_cfm}")
                                break
                    
                    if active_cfm:
                        source_cfm = active_cfm
                        print(f"DEBUG_LEGACY_SOURCE:   Using inherited CFM from active component: {source_cfm}")
                    else:
                        # Emit explicit warning and fall back to conservative default
                        try:
                            from .hvac_constants import DEFAULT_CFM_FALLBACK as _DEFAULT_CFM
                        except Exception:
                            _DEFAULT_CFM = 500.0
                        print(f"===== [PATH CALCULATOR] WARNING | Passive source has no upstream active CFM; falling back to default {float(_DEFAULT_CFM):.1f} CFM =====")
                        source_cfm = source_cfm or _DEFAULT_CFM
                
                print(f"DEBUG_LEGACY_SOURCE: Final CFM value: {source_cfm}")
                
                path_data['source_component'] = {
                    'component_type': source_comp.component_type,
                    'noise_level': source_comp.noise_level,
                    'flow_rate': source_cfm  # FIXED: Include CFM value
                }
                
                # Debug the source component data structure
                print(f"DEBUG_LEGACY_SOURCE_DATA: Created source_component data:")
                print(f"DEBUG_LEGACY_SOURCE_DATA:   Keys: {list(path_data['source_component'].keys())}")
                print(f"DEBUG_LEGACY_SOURCE_DATA:   Full data: {path_data['source_component']}")
                print(f"DEBUG_LEGACY_SOURCE_DATA:   flow_rate value: {path_data['source_component']['flow_rate']}")
                print(f"DEBUG_LEGACY_SOURCE_DATA:   flow_rate type: {type(path_data['source_component']['flow_rate'])}")
                try:
                    unit = self.find_matching_mechanical_unit(source_comp, getattr(hvac_path, 'project_id', self.project_id))
                except Exception:
                    unit = None
                bands_set = False
                if unit is not None:
                    try:
                        import json
                        origin = None
                        ob = None
                        if getattr(unit, 'outlet_levels_json', None):
                            ob = getattr(unit, 'outlet_levels_json', None); origin = 'outlet'
                        elif getattr(unit, 'inlet_levels_json', None):
                            ob = getattr(unit, 'inlet_levels_json', None); origin = 'inlet'
                        elif getattr(unit, 'radiated_levels_json', None):
                            ob = getattr(unit, 'radiated_levels_json', None); origin = 'radiated'
                        if self.debug_export_enabled:
                            print(f"DEBUG: MU '{unit.name}' band origin:", origin, 'has_data=', bool(ob))
                        octave_bands = None
                        if ob:
                            data = json.loads(ob)
                            if self.debug_export_enabled:
                                try:
                                    dtype = type(data).__name__
                                    dkeys = list(data.keys()) if hasattr(data, 'keys') else None
                                    print("DEBUG: MU bands JSON loaded:", {'type': dtype, 'keys': dkeys})
                                except Exception:
                                    pass
                            order = ["63","125","250","500","1000","2000","4000","8000"]
                            if hasattr(data, 'get'):
                                octave_bands = [float(data.get(k, 0) or 0) for k in order]
                            elif isinstance(data, list) and len(data) >= 8:
                                octave_bands = [float(x or 0) for x in data[:8]]
                            if self.debug_export_enabled:
                                print("DEBUG: MU octave_bands parsed:", octave_bands)
                        path_data['source_component']['octave_band_levels'] = octave_bands
                        bands_set = bool(octave_bands)
                        if self.debug_export_enabled:
                            print(f"DEBUG: Enriched source from matched Mechanical Unit '{unit.name}' with bands: {octave_bands}")
                    except Exception as e:
                        if self.debug_export_enabled:
                            print(f"DEBUG: Failed to enrich source with Mechanical Unit bands: {e}")
                # Fallback: if primary source had no MU bands, try the first segment's from_component (likely the fan)
                if not bands_set:
                    try:
                        first_seg = segments[0] if segments else None
                        from_comp = getattr(first_seg, 'from_component', None) if first_seg else None
                        if from_comp is not None:
                            if self.debug_export_enabled:
                                print("DEBUG: Fallback to first segment's from_component for MU bands:", {
                                    'id': getattr(from_comp, 'id', None),
                                    'type': getattr(from_comp, 'component_type', None),
                                    'name': getattr(from_comp, 'name', None),
                                })
                            mu2 = self.find_matching_mechanical_unit(from_comp, getattr(hvac_path, 'project_id', self.project_id))
                            if mu2 is not None:
                                import json
                                ob2 = (getattr(mu2, 'outlet_levels_json', None) or
                                       getattr(mu2, 'inlet_levels_json', None) or
                                       getattr(mu2, 'radiated_levels_json', None))
                                bands2 = None
                                if ob2:
                                    data2 = json.loads(ob2)
                                    order = ["63","125","250","500","1000","2000","4000","8000"]
                                    if hasattr(data2, 'get'):
                                        bands2 = [float(data2.get(k, 0) or 0) for k in order]
                                    elif isinstance(data2, list) and len(data2) >= 8:
                                        bands2 = [float(x or 0) for x in data2[:8]]
                                if bands2:
                                    # Preserve the original CFM value when overwriting with mechanical unit data
                                    original_cfm = path_data['source_component'].get('flow_rate', None)
                                    print(f"DEBUG_LEGACY_OVERWRITE: Preserving CFM value: {original_cfm}")
                                    
                                    path_data['source_component'] = {
                                        'component_type': getattr(mu2, 'unit_type', None) or 'unit',
                                        'noise_level': getattr(mu2, 'base_noise_dba', None),
                                        'octave_band_levels': bands2,
                                        'flow_rate': original_cfm  # FIXED: Preserve CFM value
                                    }
                                    if self.debug_export_enabled:
                                        print(f"DEBUG: Fallback MU match '{mu2.name}' provided bands: {bands2}")
                    except Exception as e:
                        if self.debug_export_enabled:
                            print("DEBUG: Fallback MU band extraction failed:", e)
            else:
                # 1) If primary_source_id was stored (legacy), try to interpret it as a MechanicalUnit id
                unit = None
                if getattr(hvac_path, 'primary_source_id', None):
                    unit = session.query(MechanicalUnit).filter(
                        MechanicalUnit.id == hvac_path.primary_source_id
                    ).first()

                # 2) If no direct unit link, try to match a MechanicalUnit to the first component
                matched_by_name = None
                try:
                    first_segment = segments[0]
                    if first_segment.from_component:
                        matched_by_name = self.find_matching_mechanical_unit(first_segment.from_component, getattr(hvac_path, 'project_id', self.project_id))
                except Exception:
                    matched_by_name = None

                unit = unit or matched_by_name

                if unit is not None:
                    # Parse outlet spectrum if available
                    octave_bands = None
                    try:
                        import json
                        origin = None
                        ob = None
                        if getattr(unit, 'outlet_levels_json', None):
                            ob = getattr(unit, 'outlet_levels_json', None); origin = 'outlet'
                        elif getattr(unit, 'inlet_levels_json', None):
                            ob = getattr(unit, 'inlet_levels_json', None); origin = 'inlet'
                        elif getattr(unit, 'radiated_levels_json', None):
                            ob = getattr(unit, 'radiated_levels_json', None); origin = 'radiated'
                        if self.debug_export_enabled:
                            print(f"DEBUG: MU '{unit.name}' band origin:", origin, 'has_data=', bool(ob))
                        if ob:
                            data = json.loads(ob)
                            if self.debug_export_enabled:
                                try:
                                    dtype = type(data).__name__
                                    dkeys = list(data.keys()) if hasattr(data, 'keys') else None
                                    print("DEBUG: MU bands JSON loaded:", {'type': dtype, 'keys': dkeys})
                                except Exception:
                                    pass
                            order = ["63","125","250","500","1000","2000","4000","8000"]
                            if hasattr(data, 'get'):
                                octave_bands = [float(data.get(k, 0) or 0) for k in order]
                            elif isinstance(data, list) and len(data) >= 8:
                                octave_bands = [float(x or 0) for x in data[:8]]
                            if self.debug_export_enabled:
                                print("DEBUG: MU octave_bands parsed:", octave_bands)
                    except Exception:
                        octave_bands = None
                    
                    # Do not derive A-weighted level from spectrum here; the engine uses the spectrum directly
                    noise_level = getattr(unit, 'base_noise_dba', None)
                    
                    path_data['source_component'] = {
                        'component_type': getattr(unit, 'unit_type', None) or 'unit',
                        'noise_level': noise_level,
                        'octave_band_levels': octave_bands,
                    }
                    
                    if self.debug_export_enabled:
                        noise_str = f"{float(noise_level):.1f} dB(A)" if isinstance(noise_level, (int, float)) else "n/a"
                        print(f"DEBUG: Using mechanical unit '{unit.name}' as source with {noise_str}")
                        if octave_bands:
                            print(f"DEBUG: Octave bands: {octave_bands}")
                else:
                    # 3) Fallback to first segment's from_component base noise level (no spectrum)
                    first_segment = segments[0]
                    if first_segment.from_component:
                        comp = first_segment.from_component
                        
                        # Enhanced debugging for fallback source component in legacy method
                        print(f"DEBUG_LEGACY_FALLBACK: Fallback source component found:")
                        print(f"DEBUG_LEGACY_FALLBACK:   Type: {type(comp)}")
                        print(f"DEBUG_LEGACY_FALLBACK:   ID: {getattr(comp, 'id', 'None')}")
                        print(f"DEBUG_LEGACY_FALLBACK:   Name: {getattr(comp, 'name', 'None')}")
                        print(f"DEBUG_LEGACY_FALLBACK:   Component type: {getattr(comp, 'component_type', 'None')}")
                        print(f"DEBUG_LEGACY_FALLBACK:   Noise level: {getattr(comp, 'noise_level', 'None')}")
                        print(f"DEBUG_LEGACY_FALLBACK:   CFM attribute: {getattr(comp, 'cfm', 'None')}")
                        print(f"DEBUG_LEGACY_FALLBACK:   Has CFM attr: {hasattr(comp, 'cfm')}")
                        
                        # Try to refresh the object from database
                        try:
                            session.refresh(comp)
                            print(f"DEBUG_LEGACY_FALLBACK: After refresh - CFM: {getattr(comp, 'cfm', 'None')}")
                        except Exception as e:
                            print(f"DEBUG_LEGACY_FALLBACK: Could not refresh object: {e}")
                        
                        # Try direct database query
                        try:
                            from models.hvac import HVACComponent
                            db_comp = session.query(HVACComponent).filter(HVACComponent.id == comp.id).first()
                            if db_comp:
                                print(f"DEBUG_LEGACY_FALLBACK: Direct DB query - CFM: {db_comp.cfm}")
                            else:
                                print(f"DEBUG_LEGACY_FALLBACK: Direct DB query - Component not found")
                        except Exception as e:
                            print(f"DEBUG_LEGACY_FALLBACK: Direct DB query failed: {e}")
                        
                        if self.debug_export_enabled:
                            print("DEBUG: No linked/matched MU. Using from_component as source:", {
                                'comp_id': getattr(comp, 'id', None),
                                'name': getattr(comp, 'name', None),
                                'type': getattr(comp, 'component_type', None),
                                'noise_level': getattr(comp, 'noise_level', None),
                                'cfm': getattr(comp, 'cfm', None),  # Add CFM to debug output
                            })
                        
                        # FIXED: Include CFM value in fallback source component data
                        fallback_cfm = getattr(comp, 'cfm', None)
                        print(f"DEBUG_LEGACY_FALLBACK: Using CFM value: {fallback_cfm}")
                        
                        path_data['source_component'] = {
                            'component_type': comp.component_type,
                            'noise_level': comp.noise_level,
                            'flow_rate': fallback_cfm  # FIXED: Include CFM value
                        }

            # Get terminal component
            last_segment = segments[-1]
            if last_segment.to_component:
                comp = last_segment.to_component
                path_data['terminal_component'] = {
                    'component_type': comp.component_type,
                    'noise_level': comp.noise_level
                }
            
            # Convert segments with proper flow rate propagation
            # Default origin to 'user' when not threaded from entrypoint
            effective_origin = 'user'
            try:
                # Attempt to capture origin from environment-driven background flows
                effective_origin = os.environ.get('HVAC_CALC_ORIGIN') or 'user'
            except Exception:
                effective_origin = 'user'
            try:
                effective_path_id = int(getattr(hvac_path, 'id', 0) or 0)
            except Exception:
                effective_path_id = 0
            path_data['segments'] = self._build_segments_with_flow_propagation(segments, source_cfm, effective_origin, effective_path_id)
            
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
            
            # Do NOT require octave-band spectrum; engine can estimate from dBA.
            # Ensure at least a fallback A-weighted level is present.
            try:
                src = path_data.get('source_component') or {}
                if not isinstance(src, dict):
                    src = {}
                if src.get('noise_level') is None:
                    # Try to derive a rough default from component type; final fallback 50 dB(A)
                    ctype = (src.get('component_type') or '').lower()
                    src['noise_level'] = DEFAULT_COMPONENT_NOISE_LEVELS.get(ctype, 50.0)
                    path_data['source_component'] = src
            except Exception:
                # If anything goes wrong, still allow calculation with a reasonable default
                path_data['source_component'] = {
                    'component_type': 'unit',
                    'noise_level': 50.0
                }

            # Enhanced debug export
            if self.debug_export_enabled:
                self._export_enhanced_debug_data(hvac_path, path_data)
            
            # Final debugging of path_data before return
            print(f"DEBUG_LEGACY_FINAL: Final path_data before return:")
            print(f"DEBUG_LEGACY_FINAL:   path_data keys: {list(path_data.keys())}")
            print(f"DEBUG_LEGACY_FINAL:   source_component: {path_data.get('source_component', {})}")
            print(f"DEBUG_LEGACY_FINAL:   source_component keys: {list(path_data.get('source_component', {}).keys())}")
            print(f"DEBUG_LEGACY_FINAL:   source_component flow_rate: {path_data.get('source_component', {}).get('flow_rate', 'None')}")
            print(f"DEBUG_LEGACY_FINAL:   segments count: {len(path_data.get('segments', []))}")
            
            return path_data
            
        except Exception as e:
            if self.debug_export_enabled:
                print(f"DEBUG: Session-based path data building failed: {e}")
            return None

    def _build_path_data_fallback(self, hvac_path: HVACPath) -> Optional[Dict]:
        """Fallback debug helper: log context and return None to force failure upstream."""
        try:
            if self.debug_export_enabled:
                print("DEBUG: Fallback invoked for path data build (objects may be detached). Collecting minimal debug info...")
                try:
                    seg_count = len(getattr(hvac_path, 'segments', []) or [])
                    print(f"DEBUG: Fallback: segment count={seg_count}")
                except Exception:
                    pass
            return None
        except Exception:
            return None

    def _build_segments_with_flow_propagation(self, segments: List, source_cfm: float, origin: str, path_id: int) -> List[Dict]:
        """Build segment data with proper flow rate propagation based on path topology"""
        print(f"===== [PATH CALCULATOR] BUILD SEGMENTS WITH FLOW PROPAGATION | origin={origin} | path_id={path_id} =====")
        print(f"DEBUG_FLOW_PROPAGATION: Starting flow rate propagation")
        print(f"DEBUG_FLOW_PROPAGATION:   Origin: {origin}")
        print(f"DEBUG_FLOW_PROPAGATION:   Path ID: {path_id}")
        print(f"DEBUG_FLOW_PROPAGATION:   Source CFM: {source_cfm}")
        print(f"DEBUG_FLOW_PROPAGATION:   Number of segments: {len(segments)}")
        
        segment_data_list = []
        current_flow = source_cfm
        
        for i, segment in enumerate(segments):
            segment_data = self._build_segment_data(segment)
            
            # Calculate realistic flow rate based on path position and topology
            if i == 0:
                # First segment should have the source flow rate
                calculated_flow = source_cfm
                print(f"DEBUG_FLOW_PROPAGATION:   Segment {i+1}: First segment, using source CFM: {calculated_flow}")
            else:
                # For subsequent segments, calculate based on path topology
                # This is a simplified model - in reality, you'd need more sophisticated branching logic
                calculated_flow = self._calculate_segment_flow_rate(segment, current_flow, i)
                print(f"DEBUG_FLOW_PROPAGATION:   Segment {i+1}: Calculated flow: {calculated_flow}")
            
            # Update the segment data with the calculated flow rate
            if segment_data:
                segment_data['flow_rate'] = calculated_flow
                current_flow = calculated_flow  # Update for next iteration
            
            segment_data_list.append(segment_data)
        
        # Conservation/monotonicity warning (linear path heuristic)
        try:
            flows = [sd.get('flow_rate', 0.0) for sd in segment_data_list]
            non_increasing = all((flows[j] <= flows[j-1]) for j in range(1, len(flows))) if len(flows) > 1 else True
            if not non_increasing:
                print(f"DEBUG_FLOW_PROPAGATION: WARNING - Non-monotonic flow detected along path_id={path_id} (origin={origin}). Flows: {flows}")
        except Exception:
            pass
        
        print(f"DEBUG_FLOW_PROPAGATION: Flow propagation complete")
        return segment_data_list
    
    def _calculate_segment_flow_rate(self, segment, upstream_flow: float, segment_index: int) -> float:
        """Calculate realistic flow rate for a segment based on path topology"""
        # Get the segment's original flow rate
        original_flow = getattr(segment, 'flow_rate', None)
        
        # For now, use a simple model:
        # - If original flow is reasonable (within 50% of upstream), use it
        # - Otherwise, use a fraction of upstream flow based on segment position
        
        if original_flow and 0.5 * upstream_flow <= original_flow <= 1.5 * upstream_flow:
            # Original flow is reasonable
            return original_flow
        else:
            # Calculate based on position (simplified branching model)
            # Later segments typically have lower flow rates
            flow_reduction_factor = 0.8 ** segment_index  # 20% reduction per segment
            calculated_flow = upstream_flow * flow_reduction_factor
            print(f"DEBUG_FLOW_PROPAGATION:     Original flow {original_flow} not reasonable, using calculated: {calculated_flow}")
            return calculated_flow

    def _build_segment_data(self, segment) -> Dict:
        """Build segment data dictionary from segment object with comprehensive debugging"""
        if self.debug_export_enabled:
            print(f"\nDEBUG_BUILD_SEG: Building segment data for segment ID {getattr(segment, 'id', 'unknown')}")
            print(f"DEBUG_BUILD_SEG: Raw segment attributes:")
            print(f"DEBUG_BUILD_SEG:   length = {getattr(segment, 'length', 'missing')}")
            print(f"DEBUG_BUILD_SEG:   duct_width = {getattr(segment, 'duct_width', 'missing')}")
            print(f"DEBUG_BUILD_SEG:   duct_height = {getattr(segment, 'duct_height', 'missing')}")
            print(f"DEBUG_BUILD_SEG:   diameter = {getattr(segment, 'diameter', 'missing')}")
            print(f"DEBUG_BUILD_SEG:   duct_shape = {getattr(segment, 'duct_shape', 'missing')}")
            print(f"DEBUG_BUILD_SEG:   duct_type = {getattr(segment, 'duct_type', 'missing')}")
            print(f"DEBUG_BUILD_SEG:   flow_rate = {getattr(segment, 'flow_rate', 'missing')}")
            print(f"DEBUG_BUILD_SEG:   segment_order = {getattr(segment, 'segment_order', 'missing')}")
        
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
        
        if self.debug_export_enabled:
            print(f"DEBUG_BUILD_SEG: Built segment data:")
            print(f"DEBUG_BUILD_SEG:   length = {segment_data['length']}")
            print(f"DEBUG_BUILD_SEG:   duct_width = {segment_data['duct_width']}")
            print(f"DEBUG_BUILD_SEG:   duct_height = {segment_data['duct_height']}")
            print(f"DEBUG_BUILD_SEG:   diameter = {segment_data.get('diameter', 0)}")
            print(f"DEBUG_BUILD_SEG:   duct_shape = {segment_data['duct_shape']}")
        
        # Calculate flow data with CFM priority
        try:
            # Calculate duct area
            if (segment_data['duct_shape'] or '').lower() == 'rectangular':
                width_ft = (segment_data['duct_width'] or 0.0) / 12.0
                height_ft = (segment_data['duct_height'] or 0.0) / 12.0
                area_ft2 = max(0.0, width_ft * height_ft)
            else:
                diameter_in = segment_data.get('diameter', 0.0) or 0.0
                radius_ft = (diameter_in / 2.0) / 12.0
                area_ft2 = max(0.0, 3.141592653589793 * radius_ft * radius_ft)
            
            # Priority order: segment.flow_rate → calculated from area×velocity → default CFM
            segment_cfm = getattr(segment, 'flow_rate', None)
            cfm_source = "segment_flow_rate"
            
            if not segment_cfm:
                segment_cfm = area_ft2 * DEFAULT_FLOW_VELOCITY_FPM
                cfm_source = "calculated_from_area_velocity"
            if not segment_cfm or segment_cfm <= 0:
                segment_cfm = DEFAULT_CFM_FALLBACK
                cfm_source = "default_fallback"
                
            segment_data['flow_rate'] = segment_cfm
            
            # Debug CFM assignment in segment data builder
            if self.debug_export_enabled:
                print(f"DEBUG_BUILD_SEG: Segment {getattr(segment, 'id', 'unknown')} CFM assignment:")
                print(f"DEBUG_BUILD_SEG:   Raw segment.flow_rate: {getattr(segment, 'flow_rate', 'None')}")
                print(f"DEBUG_BUILD_SEG:   Calculated from area×velocity: {area_ft2 * DEFAULT_FLOW_VELOCITY_FPM}")
                print(f"DEBUG_BUILD_SEG:   CFM source: {cfm_source}")
                print(f"DEBUG_BUILD_SEG:   Final segment CFM: {segment_cfm}")
            
            # Calculate velocity from CFM and area
            if area_ft2 > 0:
                segment_data['flow_velocity'] = segment_cfm / area_ft2  # fpm
                segment_data['flow_velocity_ft_s'] = segment_data['flow_velocity'] / 60  # ft/s for calculations
            else:
                segment_data['flow_velocity'] = DEFAULT_FLOW_VELOCITY_FPM
                segment_data['flow_velocity_ft_s'] = DEFAULT_FLOW_VELOCITY_FPM / 60

            if self.debug_export_enabled:
                print(f"DEBUG_BUILD_SEG:   flow_velocity = {segment_data['flow_velocity']:.1f} fpm")
                print(f"DEBUG_BUILD_SEG:   flow_velocity_ft_s = {segment_data['flow_velocity_ft_s']:.3f} ft/s")
                
            if self.debug_export_enabled:
                print(f"DEBUG_BUILD_SEG: Flow calculations:")
                print(f"DEBUG_BUILD_SEG:   area_ft2 = {area_ft2}")
                print(f"DEBUG_BUILD_SEG:   segment_cfm = {segment_cfm}")
                print(f"DEBUG_BUILD_SEG:   flow_velocity = {segment_data['flow_velocity']}")
                
        except Exception as e:
            if self.debug_export_enabled:
                print(f"DEBUG_BUILD_SEG: Error in flow calculations: {e}")
            segment_data['flow_rate'] = DEFAULT_CFM_FALLBACK
            segment_data['flow_velocity'] = DEFAULT_FLOW_VELOCITY_FPM
        
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
        else:
            # Infer from connected component types when no explicit fitting data is present
            try:
                from_comp_type = (getattr(segment, 'from_component', None) or getattr(segment, 'from_component', None)).component_type if getattr(segment, 'from_component', None) else ''
                to_comp_type = (getattr(segment, 'to_component', None) or getattr(segment, 'to_component', None)).component_type if getattr(segment, 'to_component', None) else ''
                fct = (from_comp_type or '').lower()
                tct = (to_comp_type or '').lower()
                # Common mappings
                if 'elbow' in fct or 'elbow' in tct:
                    segment_data['fitting_type'] = 'elbow'
                elif 'branch' in fct or 'branch' in tct or 'tee' in fct or 'tee' in tct:
                    # More specific mappings for JunctionType support via fitting_type
                    # Recognize explicit component types added to STANDARD_COMPONENTS
                    if 'junction_x' in fct or 'junction_x' in tct or 'x-junction' in fct or 'x-junction' in tct:
                        segment_data['fitting_type'] = 'x_junction'
                    elif 'branch_takeoff_90' in fct or 'branch_takeoff_90' in tct:
                        segment_data['fitting_type'] = 'branch_takeoff_90'
                    elif 'junction_t' in fct or 'junction_t' in tct or 't-junction' in fct or 't-junction' in tct:
                        segment_data['fitting_type'] = 'tee_junction'
                    else:
                        segment_data['fitting_type'] = 'junction'
                # Grille/diffuser do not change fitting_type; they are terminals
            except Exception:
                pass
        
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
                    'doas': ['DOAS', 'Ducted Outdoor Air System'],
                    'rtu': ['RTU', 'Rooftop Unit'],
                    'rf': ['RF', 'Return Fan'], 
                    'sf': ['SF', 'Supply Fan'],
                    'vav': ['VAV', 'Variable Air Volume'],
                    'fan': ['RF', 'SF', 'Fan', 'EF'],
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
        """Deprecated: standard base noise no longer used for path seeding."""
        return float('nan')
    
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
            
            # Recalculate path noise (background origin)
            os.environ['HVAC_CALC_ORIGIN'] = 'background'
            try:
                self.calculate_path_noise(segment.hvac_path_id, origin='background')
            finally:
                try:
                    del os.environ['HVAC_CALC_ORIGIN']
                except Exception:
                    pass
            
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
            
            # Recalculate path noise (background origin)
            segment = session.query(HVACSegment).filter(HVACSegment.id == segment_id).first()
            if segment:
                os.environ['HVAC_CALC_ORIGIN'] = 'background'
                try:
                    self.calculate_path_noise(segment.hvac_path_id, origin='background')
                finally:
                    try:
                        del os.environ['HVAC_CALC_ORIGIN']
                    except Exception:
                        pass
            
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