"""
HVAC Path Calculator - Calculate noise transmission through HVAC paths
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from .hvac_noise_engine import HVACNoiseEngine, PathElement, PathResult


@dataclass
class PathAnalysisResult:
    """Result of HVAC path analysis"""
    path_id: str
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
        self.noise_engine = HVACNoiseEngine()
    
    def create_hvac_path_from_drawing(self, project_id: str, drawing_data: Dict) -> Optional[Dict]:
        """
        Create HVAC path from drawing elements (components and segments)
        
        Args:
            project_id: Project ID
            drawing_data: Dictionary containing components and segments from drawing
            
        Returns:
            Created HVAC path data or None if creation failed
        """
        try:
            components = drawing_data.get('components', [])
            segments = drawing_data.get('segments', [])
            
            if len(components) < 2:
                raise ValueError("Need at least 2 components to create HVAC path")
            
            if len(segments) == 0:
                raise ValueError("Need at least 1 segment to connect components")
            
            # Convert drawing data to path elements
            path_elements = self._convert_drawing_to_path_elements(components, segments)
            
            # Calculate noise for the new path
            result = self.noise_engine.calculate_path_noise(path_elements, f"path_{project_id}")
            
            # Create path data structure
            path_data = {
                'path_id': f"path_{project_id}",
                'path_name': f"Path: {components[0].get('component_type', 'unknown')} to {components[-1].get('component_type', 'unknown')}",
                'description': f"HVAC path from {components[0].get('name', 'source')} to {components[-1].get('name', 'terminal')}",
                'path_type': 'supply',
                'elements': path_elements,
                'calculation_result': result,
                'project_id': project_id
            }
            
            return path_data
            
        except Exception as e:
            print(f"Error creating HVAC path: {e}")
            return None
    
    def _convert_drawing_to_path_elements(self, components: List[Dict], segments: List[Dict]) -> List[PathElement]:
        """Convert drawing components and segments to PathElement objects"""
        elements = []
        
        # Add source component
        if components:
            source_comp = components[0]
            source_element = PathElement(
                element_type='source',
                element_id=f"source_{source_comp.get('id', 1)}",
                source_noise_level=self.get_component_noise_level(source_comp.get('component_type', '')),
                octave_band_levels=source_comp.get('octave_band_levels')
            )
            elements.append(source_element)
        
        # Add segments
        for i, seg_data in enumerate(segments):
            element_type = self._determine_segment_type(seg_data)
            
            element = PathElement(
                element_type=element_type,
                element_id=f"segment_{i+1}",
                length=seg_data.get('length_real', 0.0),
                width=seg_data.get('duct_width', 12.0),
                height=seg_data.get('duct_height', 8.0),
                diameter=seg_data.get('diameter', 0.0),
                duct_shape=seg_data.get('duct_shape', 'rectangular'),
                duct_type=seg_data.get('duct_type', 'sheet_metal'),
                lining_thickness=seg_data.get('lining_thickness', 0.0),
                flow_rate=seg_data.get('flow_rate', 0.0),
                flow_velocity=seg_data.get('flow_velocity', 0.0),
                pressure_drop=seg_data.get('pressure_drop', 0.0),
                vane_chord_length=seg_data.get('vane_chord_length', 0.0),
                num_vanes=seg_data.get('num_vanes', 0),
                room_volume=seg_data.get('room_volume', 0.0),
                room_absorption=seg_data.get('room_absorption', 0.0)
            )
            elements.append(element)
        
        # Add terminal component
        if len(components) > 1:
            terminal_comp = components[-1]
            terminal_element = PathElement(
                element_type='terminal',
                element_id=f"terminal_{terminal_comp.get('id', len(components))}",
                source_noise_level=self.get_component_noise_level(terminal_comp.get('component_type', '')),
                room_volume=terminal_comp.get('room_volume', 0.0),
                room_absorption=terminal_comp.get('room_absorption', 0.0)
            )
            elements.append(terminal_element)
        
        return elements
    
    def _determine_segment_type(self, segment_data: Dict) -> str:
        """Determine the element type based on segment properties"""
        if segment_data.get('duct_type') == 'flexible':
            return 'flex_duct'
        elif segment_data.get('fitting_type') == 'elbow':
            return 'elbow'
        elif segment_data.get('fitting_type') == 'junction':
            return 'junction'
        else:
            return 'duct'
    
    def calculate_path_noise(self, path_id: str, path_elements: List[PathElement]) -> PathAnalysisResult:
        """
        Calculate noise for a specific HVAC path
        
        Args:
            path_id: HVAC path ID
            path_elements: List of PathElement objects defining the path
            
        Returns:
            PathAnalysisResult with calculation details
        """
        try:
            # Perform calculation using the noise engine
            calc_results = self.noise_engine.calculate_path_noise(path_elements, path_id)
            
            # Create result object
            result = PathAnalysisResult(
                path_id=path_id,
                path_name=f"Path {path_id}",
                source_noise=calc_results.source_noise_dba,
                terminal_noise=calc_results.terminal_noise_dba,
                total_attenuation=calc_results.total_attenuation_dba,
                nc_rating=calc_results.nc_rating,
                calculation_valid=calc_results.calculation_valid,
                segment_results=calc_results.element_results,
                warnings=calc_results.warnings,
                error_message=calc_results.error_message
            )
            
            return result
            
        except Exception as e:
            return PathAnalysisResult(
                path_id=path_id,
                path_name=f"Path {path_id}",
                source_noise=0.0,
                terminal_noise=0.0,
                total_attenuation=0.0,
                nc_rating=0,
                calculation_valid=False,
                segment_results=[],
                warnings=[],
                error_message=str(e)
            )
    
    def calculate_all_project_paths(self, project_paths: List[Dict]) -> List[PathAnalysisResult]:
        """
        Calculate noise for all HVAC paths in a project
        
        Args:
            project_paths: List of project path data dictionaries
            
        Returns:
            List of PathAnalysisResult objects
        """
        results = []
        
        try:
            for path_data in project_paths:
                path_elements = path_data.get('elements', [])
                path_id = path_data.get('path_id', 'unknown')
                
                result = self.calculate_path_noise(path_id, path_elements)
                results.append(result)
            
        except Exception as e:
            print(f"Error calculating project paths: {e}")
        
        return results

    def analyze_hvac_path(self, path_id: str, path_elements: List[PathElement]) -> Optional[PathAnalysisResult]:
        """
        Analyze a specific HVAC path and return detailed results
        
        Args:
            path_id: HVAC path ID
            path_elements: List of PathElement objects defining the path
            
        Returns:
            PathAnalysisResult with analysis details or None if failed
        """
        try:
            return self.calculate_path_noise(path_id, path_elements)
        except Exception as e:
            print(f"Error analyzing HVAC path {path_id}: {e}")
            return None
    
    def update_segment_properties(self, path_elements: List[PathElement], 
                                segment_id: str, properties: Dict) -> List[PathElement]:
        """
        Update HVAC segment properties
        
        Args:
            path_elements: List of current path elements
            segment_id: Segment ID to update
            properties: Dictionary of properties to update
            
        Returns:
            Updated list of path elements
        """
        try:
            updated_elements = []
            
            for element in path_elements:
                if element.element_id == segment_id:
                    # Update properties
                    for key, value in properties.items():
                        if hasattr(element, key):
                            setattr(element, key, value)
                
                updated_elements.append(element)
            
            return updated_elements
            
        except Exception as e:
            print(f"Error updating segment properties: {e}")
            return path_elements
    
    def add_segment_fitting(self, path_elements: List[PathElement], 
                          segment_id: str, fitting_type: str, 
                          position: float = 0.0) -> List[PathElement]:
        """
        Add fitting to HVAC segment
        
        Args:
            path_elements: List of current path elements
            segment_id: Segment ID to add fitting to
            fitting_type: Type of fitting
            position: Position on segment (feet from start)
            
        Returns:
            Updated list of path elements
        """
        try:
            updated_elements = []
            
            for element in path_elements:
                if element.element_id == segment_id:
                    # Update element type based on fitting
                    if fitting_type == 'elbow':
                        element.element_type = 'elbow'
                    elif fitting_type == 'junction':
                        element.element_type = 'junction'
                    elif fitting_type == 'turning_vanes':
                        element.num_vanes = 3  # Default number of vanes
                        element.vane_chord_length = 2.0  # Default vane chord length
                
                updated_elements.append(element)
            
            return updated_elements
            
        except Exception as e:
            print(f"Error adding segment fitting: {e}")
            return path_elements
    
    def get_path_summary(self, project_paths: List[Dict]) -> Dict:
        """
        Get summary of all HVAC paths in project
        
        Args:
            project_paths: List of project path data dictionaries
            
        Returns:
            Summary dictionary
        """
        try:
            summary: Dict[str, Any] = {
                'total_paths': len(project_paths),
                'calculated_paths': 0,
                'avg_noise_level': 0.0,
                'avg_nc_rating': 0.0,
                'paths_by_type': {},
                'paths_over_nc45': 0
            }
            
            total_noise: float = 0.0
            total_nc: float = 0.0
            
            for path_data in project_paths:
                calc_result = path_data.get('calculation_result')
                if calc_result and hasattr(calc_result, 'calculation_valid') and calc_result.calculation_valid:
                    summary['calculated_paths'] += 1
                    if hasattr(calc_result, 'terminal_noise_dba'):
                        total_noise += calc_result.terminal_noise_dba
                    
                    if hasattr(calc_result, 'nc_rating') and calc_result.nc_rating > 0:
                        total_nc += calc_result.nc_rating
                        if calc_result.nc_rating > 45:
                            summary['paths_over_nc45'] += 1
                
                # Count by type
                path_type = path_data.get('path_type', 'unknown')
                if path_type in summary['paths_by_type']:
                    summary['paths_by_type'][path_type] += 1
                else:
                    summary['paths_by_type'][path_type] = 1
            
            if summary['calculated_paths'] > 0:
                summary['avg_noise_level'] = total_noise / summary['calculated_paths']
                summary['avg_nc_rating'] = total_nc / summary['calculated_paths']
            
            return summary
            
        except Exception as e:
            print(f"Error getting path summary: {e}")
            return {
                'total_paths': 0,
                'calculated_paths': 0,
                'avg_noise_level': 0.0,
                'avg_nc_rating': 0.0,
                'paths_by_type': {},
                'paths_over_nc45': 0
            }
    
    def export_path_results(self, project_paths: List[Dict]) -> List[Dict]:
        """
        Export HVAC path results for Excel/reporting
        
        Args:
            project_paths: List of project path data dictionaries
            
        Returns:
            List of path result dictionaries
        """
        results = []
        
        try:
            for path_data in project_paths:
                calc_result = path_data.get('calculation_result')
                elements = path_data.get('elements', [])
                
                result = {
                    'Path Name': path_data.get('path_name', 'Unknown'),
                    'Path Type': path_data.get('path_type', 'supply'),
                    'Description': path_data.get('description', ''),
                    'Calculated Noise (dB)': calc_result.terminal_noise_dba if calc_result else 0,
                    'NC Rating': calc_result.nc_rating if calc_result else 0,
                    'Segment Count': len([e for e in elements if e.element_type != 'source' and e.element_type != 'terminal']),
                    'Total Length (ft)': sum(e.length for e in elements if e.element_type == 'duct'),
                    'Source Noise (dB)': calc_result.source_noise_dba if calc_result else 0,
                    'Total Attenuation (dB)': calc_result.total_attenuation_dba if calc_result else 0
                }
                results.append(result)
            
        except Exception as e:
            print(f"Error exporting path results: {e}")
        
        return results
    
    def get_component_noise_level(self, component_type: str) -> float:
        """Get standard noise level for component type"""
        # Standard component noise levels (dB(A))
        standard_levels = {
            'air_handler': 75.0,
            'fan': 80.0,
            'chiller': 85.0,
            'boiler': 70.0,
            'terminal_unit': 45.0,
            'diffuser': 25.0,
            'grille': 20.0,
            'vav_box': 50.0,
            'damper': 30.0,
            'filter': 35.0
        }
        
        return standard_levels.get(component_type.lower(), 50.0)
    
    def validate_path_elements(self, path_elements: List[PathElement]) -> Tuple[bool, List[str]]:
        """Validate path elements for calculation"""
        return self.noise_engine.validate_path_elements(path_elements)