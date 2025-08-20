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
from .noise_calculator import NoiseCalculator
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
    
    def __init__(self):
        """Initialize the HVAC path calculator"""
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
            
            session = get_session()
            
            # Create HVAC components in database
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
                db_components[len(db_components)] = hvac_comp
            
            # Create HVAC path
            source_comp = db_components[0]
            terminal_comp = db_components[len(db_components)-1]
            
            hvac_path = HVACPath(
                project_id=project_id,
                name=f"Path: {source_comp.component_type.upper()} to {terminal_comp.component_type.upper()}",
                description=f"HVAC path from {source_comp.name} to {terminal_comp.name}",
                path_type='supply'
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

            session.commit()
            
            # Calculate noise for the new path (uses any saved source/receiver if available later)
            self.calculate_path_noise(hvac_path.id)
            
            session.close()
            return hvac_path
            
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
            print(f"Error creating HVAC path: {e}")
            return None
    
    def calculate_path_noise(self, path_id: int, debug: bool = False) -> PathAnalysisResult:
        """
        Calculate noise for a specific HVAC path
        
        Args:
            path_id: HVAC path ID
            
        Returns:
            PathAnalysisResult with calculation details
        """
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
        try:
            # Always refetch the path with eager-loaded relationships to avoid
            # lazy-loading on detached instances coming from the UI layer.
            try:
                path_id = getattr(hvac_path, 'id', None) if not isinstance(hvac_path, int) else int(hvac_path)
                if path_id is None:
                    raise ValueError("HVACPath id is required to build path data")
                _sess = get_session()
                try:
                    hvac_path = (
                        _sess.query(HVACPath)
                        .options(
                            selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                            selectinload(HVACPath.segments).selectinload(HVACSegment.to_component),
                            selectinload(HVACPath.segments).selectinload(HVACSegment.fittings),
                            selectinload(HVACPath.primary_source),
                        )
                        .filter(HVACPath.id == path_id)
                        .first()
                    )
                finally:
                    try:
                        _sess.close()
                    except Exception:
                        pass
            except Exception:
                # Fall through and hope provided object is usable
                pass
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
                # Use primary_source_id directly to avoid triggering a lazy-load
                preferred_source_id = getattr(hvac_path, 'primary_source_id', None)
                segments = self._order_segments_by_connectivity(list(segments), preferred_source_component_id=preferred_source_id)
            except Exception as e:
                print(f"DEBUG: Using stored segment order; connectivity ordering failed: {e}")

            # Get source: prefer explicit HVACComponent relationship; fallback to MechanicalUnit id (legacy),
            # otherwise use the first segment's from_component.
            source_comp = None
            try:
                source_comp = getattr(hvac_path, 'primary_source', None)
            except Exception:
                source_comp = None

            if source_comp is not None:
                path_data['source_component'] = {
                    'component_type': source_comp.component_type,
                    'noise_level': source_comp.noise_level or self.get_component_noise_level(source_comp.component_type)
                }
            else:
                # Backward compatibility: interpret primary_source_id as MechanicalUnit id if no component is linked
                unit = None
                try:
                    if getattr(hvac_path, 'primary_source_id', None):
                        sess2 = get_session()
                        try:
                            unit = sess2.query(MechanicalUnit).filter(MechanicalUnit.id == hvac_path.primary_source_id).first()
                        finally:
                            try:
                                sess2.close()
                            except Exception:
                                pass
                except Exception:
                    unit = None

                if unit is not None:
                    # Parse outlet spectrum if available
                    octave_bands = None
                    try:
                        import json
                        ob = getattr(unit, 'outlet_levels_json', None) or getattr(unit, 'inlet_levels_json', None) or getattr(unit, 'radiated_levels_json', None)
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
                else:
                    first_segment = segments[0]
                    if first_segment.from_component:
                        comp = first_segment.from_component
                        path_data['source_component'] = {
                            'component_type': comp.component_type,
                            'noise_level': comp.noise_level or self.get_component_noise_level(comp.component_type)
                        }
            
            # Get terminal component (to last segment)
            last_segment = segments[-1]
            if last_segment.to_component:
                comp = last_segment.to_component
                path_data['terminal_component'] = {
                    'component_type': comp.component_type,
                    'noise_level': comp.noise_level or self.get_component_noise_level(comp.component_type)
                }
            
            # Convert segments
            for segment in segments:
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
                # Provide default flow data if missing: assume 800 fpm typical duct velocity
                try:
                    if (segment_data['duct_shape'] or '').lower() == 'rectangular':
                        width_ft = (segment_data['duct_width'] or 0.0) / 12.0
                        height_ft = (segment_data['duct_height'] or 0.0) / 12.0
                        area_ft2 = max(0.0, width_ft * height_ft)
                    else:
                        diameter_in = segment_data.get('diameter', 0.0) or 0.0
                        radius_ft = (diameter_in / 2.0) / 12.0
                        area_ft2 = max(0.0, 3.141592653589793 * radius_ft * radius_ft)
                    # Use 800 fpm if velocity/flow not stored
                    default_velocity_fpm = 800.0
                    segment_data['flow_velocity'] = getattr(segment, 'flow_velocity', None) or default_velocity_fpm
                    segment_data['flow_rate'] = getattr(segment, 'flow_rate', None) or (area_ft2 * default_velocity_fpm)
                except Exception:
                    # If geometry invalid, leave flow fields absent
                    pass
                
                # Add fittings
                for fitting in segment.fittings:
                    fitting_data = {
                        'fitting_type': fitting.fitting_type,
                        'noise_adjustment': fitting.noise_adjustment or self.get_fitting_noise_adjustment(fitting.fitting_type),
                        'position': getattr(fitting, 'position_on_segment', 0.0) or 0.0
                    }
                    segment_data['fittings'].append(fitting_data)

                # Derive a fitting_type for engine element inference
                # Prefer the first specific fitting name (e.g., 'elbow_90', 'tee_branch') if available;
                # fallback to high-level 'elbow' or 'junction'
                fitting_types = [f.get('fitting_type', '') for f in segment_data['fittings']]
                inferred_type = None
                specific_type = None
                for ft in fitting_types:
                    lower_ft = (ft or '').lower()
                    if not specific_type and lower_ft:
                        specific_type = lower_ft
                    if lower_ft.startswith('elbow'):
                        inferred_type = 'elbow'
                        # still keep specific type recorded
                    if 'tee' in lower_ft or 'junction' in lower_ft:
                        inferred_type = inferred_type or 'junction'
                if specific_type:
                    segment_data['fitting_type'] = specific_type
                elif inferred_type:
                    segment_data['fitting_type'] = inferred_type
                
                path_data['segments'].append(segment_data)
            
            return path_data
            
        except Exception as e:
            print(f"Error building path data: {e}")
            return None

    def _order_segments_by_connectivity(self, segments: List[HVACSegment], preferred_source_component_id: Optional[int] = None) -> List[HVACSegment]:
        """Order segments by walking the chain from source to terminal.

        - If a preferred source component id is provided and exists in the chain, start from there.
        - Otherwise, start from a component that appears as a 'from' but never as a 'to'.
        - Fall back to existing segment_order if traversal fails.
        """
        try:
            if not segments:
                return []

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
            if preferred_source_component_id and preferred_source_component_id in from_map:
                start_comp_id = preferred_source_component_id
            else:
                # A 'from' that is never a 'to' is a likely source
                candidates = [fcid for fcid in from_map.keys() if fcid not in to_set]
                if candidates:
                    start_comp_id = candidates[0]
                else:
                    # Fallback: choose the lowest segment_order's from_component
                    try:
                        first_seg = sorted(segments, key=lambda s: getattr(s, 'segment_order', 0))[0]
                        start_comp_id = getattr(first_seg, 'from_component_id', None)
                    except Exception:
                        start_comp_id = None

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
                    break
                if seg.id in visited:
                    # Loop detected
                    break
                ordered.append(seg)
                visited.add(seg.id)
                current = getattr(seg, 'to_component_id', None)

            # If traversal did not include all segments, append remaining by existing order
            if len(ordered) < len(segments):
                remaining = [s for s in sorted(segments, key=lambda s: getattr(s, 'segment_order', 0)) if s.id not in visited]
                ordered.extend(remaining)

            return ordered if ordered else list(sorted(segments, key=lambda s: getattr(s, 'segment_order', 0)))
        except Exception:
            return list(sorted(segments, key=lambda s: getattr(s, 'segment_order', 0)))
    
    def get_component_noise_level(self, component_type: str) -> float:
        """Get standard noise level for component type"""
        return STANDARD_COMPONENTS.get(component_type, {}).get('noise_level', 50.0)
    
    def get_fitting_noise_adjustment(self, fitting_type: str) -> float:
        """Get standard noise adjustment for fitting type"""
        return STANDARD_FITTINGS.get(fitting_type, {}).get('noise_adjustment', 0.0)
    
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