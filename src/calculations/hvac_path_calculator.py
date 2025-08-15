"""
HVAC Path Calculator - Complete HVAC path noise analysis system
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from models import get_session
from models.hvac import HVACPath, HVACSegment, HVACComponent, SegmentFitting
from models.mechanical import MechanicalUnit
from data.components import STANDARD_COMPONENTS, STANDARD_FITTINGS
from .noise_calculator import NoiseCalculator


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


class HVACPathCalculator:
    """Comprehensive HVAC path noise calculation and management system"""
    
    def __init__(self):
        """Initialize the HVAC path calculator"""
        self.noise_calculator = NoiseCalculator()
    
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
    
    def calculate_path_noise(self, path_id: int) -> PathAnalysisResult:
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
            calc_results = self.noise_calculator.calculate_hvac_path_noise(path_data)
            
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
                error_message=calc_results.get('error')
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
                preferred_source_id = getattr(getattr(hvac_path, 'primary_source', None), 'id', None)
                segments = self._order_segments_by_connectivity(list(segments), preferred_source_component_id=preferred_source_id)
            except Exception as e:
                print(f"DEBUG: Using stored segment order; connectivity ordering failed: {e}")

            # Get source: prefer selected MechanicalUnit (primary_source), otherwise first segment's from_component
            unit = None
            # Case 1: Relationship points to HVACComponent (schema FK) – try to look up MechanicalUnit by id if present
            try:
                if getattr(hvac_path, 'primary_source_id', None):
                    # Attempt to resolve a MechanicalUnit with the same id (stored by the dialog)
                    sess2 = get_session()
                    try:
                        mu = sess2.query(MechanicalUnit).filter(MechanicalUnit.id == hvac_path.primary_source_id).first()
                        unit = mu if mu is not None else None
                    finally:
                        try:
                            sess2.close()
                        except Exception:
                            pass
            except Exception:
                unit = None

            # Case 2: If relationship actually references a MechanicalUnit-like object (defensive)
            if unit is None and hvac_path.primary_source is not None:
                obj = hvac_path.primary_source
                if hasattr(obj, 'unit_type') or hasattr(obj, 'outlet_levels_json'):
                    unit = obj  # Treat as MechanicalUnit-like

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
                
                # Add fittings
                for fitting in segment.fittings:
                    fitting_data = {
                        'fitting_type': fitting.fitting_type,
                        'noise_adjustment': fitting.noise_adjustment or self.get_fitting_noise_adjustment(fitting.fitting_type),
                        'position': getattr(fitting, 'position_on_segment', 0.0) or 0.0
                    }
                    segment_data['fittings'].append(fitting_data)

                # Derive a high-level fitting_type for engine element inference
                # Map any elbow_* fitting to 'elbow', any tee_* to 'junction'
                fitting_types = [f.get('fitting_type', '') for f in segment_data['fittings']]
                inferred_type = None
                for ft in fitting_types:
                    lower_ft = (ft or '').lower()
                    if lower_ft.startswith('elbow'):
                        inferred_type = 'elbow'
                        break
                    if 'tee' in lower_ft or 'junction' in lower_ft:
                        inferred_type = 'junction'
                        # keep searching for elbow only if needed; junction is acceptable
                if inferred_type:
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