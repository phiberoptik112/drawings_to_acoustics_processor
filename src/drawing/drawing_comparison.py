"""
Drawing comparison engine for detecting changes between drawing sets
"""

import json
import math
from typing import List, Dict
from datetime import datetime
from dataclasses import dataclass

from models import (
    get_session,
    DrawingSet,
    DrawingComparison,
    ChangeItem,
    Space,
)
from models.hvac import HVACComponent, HVACPath
from models.drawing import Drawing
from calculations import RT60Calculator, NoiseCalculator


@dataclass
class GeometricMatch:
    """Represents a geometric match between elements in different sets"""
    base_element: object
    compare_element: object
    similarity_score: float
    geometric_changes: dict


class DrawingComparisonEngine:
    """Engine for comparing two drawing sets and detecting changes"""
    
    def __init__(self):
        self.rt60_calculator = RT60Calculator()
        self.noise_calculator = NoiseCalculator()
        
        # Thresholds for matching
        self.POSITION_TOLERANCE = 50.0  # pixels
        self.AREA_TOLERANCE = 0.1  # 10% area difference
        self.SIMILARITY_THRESHOLD = 0.7  # Minimum similarity for matching
    
    def compare_drawing_sets(self, base_set_id: int, compare_set_id: int) -> DrawingComparison:
        """
        Compare two drawing sets and return detailed comparison
        """
        session = get_session()
        try:
            base_set = session.query(DrawingSet).filter(DrawingSet.id == base_set_id).first()
            compare_set = session.query(DrawingSet).filter(DrawingSet.id == compare_set_id).first()
            
            if not base_set or not compare_set:
                raise ValueError("Invalid drawing set IDs")
            
            # Create comparison record
            comparison = DrawingComparison(
                project_id=base_set.project_id,
                base_set_id=base_set_id,
                compare_set_id=compare_set_id,
                comparison_date=datetime.utcnow(),
            )
            session.add(comparison)
            session.flush()  # Get ID
            
            # Collect all changes
            all_changes: List[Dict] = []
            
            # 1. Compare spaces
            base_spaces = self._get_spaces_for_set(session, base_set_id)
            compare_spaces = self._get_spaces_for_set(session, compare_set_id)
            space_changes = self.detect_space_changes(base_spaces, compare_spaces)
            all_changes.extend(space_changes)
            
            # 2. Compare HVAC components
            base_hvac = self._get_hvac_components_for_set(session, base_set_id)
            compare_hvac = self._get_hvac_components_for_set(session, compare_set_id)
            hvac_changes = self.detect_hvac_changes(base_hvac, compare_hvac)
            all_changes.extend(hvac_changes)
            
            # 3. Compare HVAC paths
            base_paths = self._get_hvac_paths_for_set(session, base_set_id)
            compare_paths = self._get_hvac_paths_for_set(session, compare_set_id)
            path_changes = self.detect_path_changes(base_paths, compare_paths)
            all_changes.extend(path_changes)
            
            # Create change items and analyze acoustic impact
            critical_changes = 0
            total_acoustic_impact = 0.0
            
            for change_data in all_changes:
                change_item = ChangeItem(
                    comparison_id=comparison.id,
                    element_type=change_data['element_type'],
                    change_type=change_data['change_type'],
                    base_element_id=change_data.get('base_element_id'),
                    compare_element_id=change_data.get('compare_element_id'),
                    change_details=json.dumps(change_data['details']),
                    drawing_id=change_data.get('drawing_id'),
                    x_position=change_data.get('x_position'),
                    y_position=change_data.get('y_position'),
                    area_change=change_data.get('area_change'),
                    position_delta=change_data.get('position_delta'),
                )
                
                # Analyze acoustic impact
                acoustic_impact = self.analyze_acoustic_impact(change_data)
                change_item.acoustic_impact = json.dumps(acoustic_impact)
                change_item.severity = acoustic_impact.get('severity', 'medium')
                
                if change_item.severity == 'critical':
                    critical_changes += 1
                
                session.add(change_item)
                total_acoustic_impact += acoustic_impact.get('impact_score', 0)
            
            # Update comparison summary
            comparison.total_changes = len(all_changes)
            comparison.critical_changes = critical_changes
            comparison.acoustic_impact_score = total_acoustic_impact / max(len(all_changes), 1)
            comparison.comparison_results = json.dumps({
                'summary': {
                    'total_changes': len(all_changes),
                    'space_changes': len([c for c in all_changes if c['element_type'] == 'space']),
                    'hvac_changes': len([c for c in all_changes if c['element_type'] == 'hvac_component']),
                    'path_changes': len([c for c in all_changes if c['element_type'] == 'hvac_path']),
                    'critical_changes': critical_changes,
                }
            })
            
            session.commit()
            return comparison
            
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def detect_space_changes(self, base_spaces: List[Space], compare_spaces: List[Space]) -> List[dict]:
        """Detect changes in room layouts and spaces"""
        changes: List[dict] = []
        
        # Match spaces using geometric similarity
        matches = self._match_spaces_by_geometry(base_spaces, compare_spaces)
        
        # Track which spaces have been matched
        matched_base = set()
        matched_compare = set()
        
        # Process matches and detect modifications
        for match in matches:
            if match.similarity_score >= self.SIMILARITY_THRESHOLD:
                matched_base.add(match.base_element.id)
                matched_compare.add(match.compare_element.id)
                
                # Check for modifications
                if match.geometric_changes:
                    changes.append({
                        'element_type': 'space',
                        'change_type': 'modified',
                        'base_element_id': match.base_element.id,
                        'compare_element_id': match.compare_element.id,
                        'details': {
                            'name': match.compare_element.name,
                            'geometric_changes': match.geometric_changes,
                            'base_area': match.base_element.floor_area,
                            'compare_area': match.compare_element.floor_area,
                        },
                        'drawing_id': match.compare_element.drawing_id,
                        'area_change': (match.compare_element.floor_area or 0) - (match.base_element.floor_area or 0),
                        'position_delta': 0.0,
                    })
        
        # Detect additions (spaces in compare set but not matched)
        for space in compare_spaces:
            if space.id not in matched_compare:
                changes.append({
                    'element_type': 'space',
                    'change_type': 'added',
                    'compare_element_id': space.id,
                    'details': {
                        'name': space.name,
                        'area': space.floor_area,
                        'height': space.ceiling_height,
                    },
                    'drawing_id': space.drawing_id,
                    'area_change': space.floor_area or 0,
                })
        
        # Detect removals (spaces in base set but not matched)
        for space in base_spaces:
            if space.id not in matched_base:
                changes.append({
                    'element_type': 'space',
                    'change_type': 'removed',
                    'base_element_id': space.id,
                    'details': {
                        'name': space.name,
                        'area': space.floor_area,
                        'height': space.ceiling_height,
                    },
                    'drawing_id': space.drawing_id,
                    'area_change': -(space.floor_area or 0),
                })
        
        return changes
    
    def detect_hvac_changes(self, base_components: List[HVACComponent], compare_components: List[HVACComponent]) -> List[dict]:
        """Detect changes in HVAC components"""
        changes: List[dict] = []
        
        # Match HVAC components by position and type
        matches = self._match_hvac_by_position(base_components, compare_components)
        
        matched_base = set()
        matched_compare = set()
        
        # Process matches
        for match in matches:
            if match.similarity_score >= self.SIMILARITY_THRESHOLD:
                matched_base.add(match.base_element.id)
                matched_compare.add(match.compare_element.id)
                
                # Check for modifications
                if match.geometric_changes:
                    changes.append({
                        'element_type': 'hvac_component',
                        'change_type': 'modified',
                        'base_element_id': match.base_element.id,
                        'compare_element_id': match.compare_element.id,
                        'details': {
                            'name': match.compare_element.name,
                            'component_type': match.compare_element.component_type,
                            'changes': match.geometric_changes,
                        },
                        'drawing_id': match.compare_element.drawing_id,
                        'x_position': match.compare_element.x_position,
                        'y_position': match.compare_element.y_position,
                        'position_delta': match.geometric_changes.get('position_delta', 0),
                    })
        
        # Detect additions
        for component in compare_components:
            if component.id not in matched_compare:
                changes.append({
                    'element_type': 'hvac_component',
                    'change_type': 'added',
                    'compare_element_id': component.id,
                    'details': {
                        'name': component.name,
                        'component_type': component.component_type,
                        'noise_level': component.noise_level,
                    },
                    'drawing_id': component.drawing_id,
                    'x_position': component.x_position,
                    'y_position': component.y_position,
                })
        
        # Detect removals
        for component in base_components:
            if component.id not in matched_base:
                changes.append({
                    'element_type': 'hvac_component',
                    'change_type': 'removed',
                    'base_element_id': component.id,
                    'details': {
                        'name': component.name,
                        'component_type': component.component_type,
                        'noise_level': component.noise_level,
                    },
                    'drawing_id': component.drawing_id,
                    'x_position': component.x_position,
                    'y_position': component.y_position,
                })
        
        return changes
    
    def detect_path_changes(self, base_paths: List[HVACPath], compare_paths: List[HVACPath]) -> List[dict]:
        """Detect changes in HVAC paths"""
        changes: List[dict] = []
        
        # Simple name-based matching for paths
        base_path_names = {path.name: path for path in base_paths if getattr(path, 'name', None)}
        compare_path_names = {path.name: path for path in compare_paths if getattr(path, 'name', None)}
        
        # Find modifications
        for name in base_path_names.keys() & compare_path_names.keys():
            base_path = base_path_names[name]
            compare_path = compare_path_names[name]
            
            path_changes = {}
            
            # Check for target space changes
            if getattr(base_path, 'target_space_id', None) != getattr(compare_path, 'target_space_id', None):
                path_changes['target_space_changed'] = True
            
            # Check for segment count changes
            base_segments = len(getattr(base_path, 'segments', []) or [])
            compare_segments = len(getattr(compare_path, 'segments', []) or [])
            if base_segments != compare_segments:
                path_changes['segment_count_changed'] = {
                    'from': base_segments,
                    'to': compare_segments,
                }
            
            if path_changes:
                changes.append({
                    'element_type': 'hvac_path',
                    'change_type': 'modified',
                    'base_element_id': base_path.id,
                    'compare_element_id': compare_path.id,
                    'details': {
                        'name': name,
                        'path_type': getattr(compare_path, 'path_type', None),
                        'changes': path_changes,
                    },
                })
        
        # Additions
        for name in compare_path_names.keys() - base_path_names.keys():
            path = compare_path_names[name]
            changes.append({
                'element_type': 'hvac_path',
                'change_type': 'added',
                'compare_element_id': path.id,
                'details': {
                    'name': name,
                    'path_type': getattr(path, 'path_type', None),
                    'target_space_id': getattr(path, 'target_space_id', None),
                },
            })
        
        # Removals
        for name in base_path_names.keys() - compare_path_names.keys():
            path = base_path_names[name]
            changes.append({
                'element_type': 'hvac_path',
                'change_type': 'removed',
                'base_element_id': path.id,
                'details': {
                    'name': name,
                    'path_type': getattr(path, 'path_type', None),
                    'target_space_id': getattr(path, 'target_space_id', None),
                },
            })
        
        return changes
    
    def analyze_acoustic_impact(self, change_data: dict) -> dict:
        """Analyze acoustic impact of detected changes"""
        impact = {
            'impact_score': 0,  # 0-100 scale
            'severity': 'low',
            'rt60_impact': None,
            'noise_impact': None,
            'recommendations': [],
        }
        
        element_type = change_data['element_type']
        change_type = change_data['change_type']
        
        if element_type == 'space':
            impact.update(self._analyze_space_acoustic_impact(change_data))
        elif element_type == 'hvac_component':
            impact.update(self._analyze_hvac_acoustic_impact(change_data))
        elif element_type == 'hvac_path':
            impact.update(self._analyze_path_acoustic_impact(change_data))
        
        # Determine severity based on impact score
        if impact['impact_score'] >= 80:
            impact['severity'] = 'critical'
        elif impact['impact_score'] >= 60:
            impact['severity'] = 'high'
        elif impact['impact_score'] >= 30:
            impact['severity'] = 'medium'
        else:
            impact['severity'] = 'low'
        
        return impact
    
    # Helper methods
    def _get_spaces_for_set(self, session, set_id: int) -> List[Space]:
        """Get all spaces associated with drawings in a set"""
        return (
            session.query(Space)
            .join(Drawing)
            .filter(Drawing.drawing_set_id == set_id)
            .all()
        )
    
    def _get_hvac_components_for_set(self, session, set_id: int) -> List[HVACComponent]:
        """Get all HVAC components associated with drawings in a set"""
        return (
            session.query(HVACComponent)
            .join(Drawing)
            .filter(Drawing.drawing_set_id == set_id)
            .all()
        )
    
    def _get_hvac_paths_for_set(self, session, set_id: int) -> List[HVACPath]:
        """Get all HVAC paths associated with a drawing set (project-level, not directly bound to set)"""
        project_id = session.query(DrawingSet.project_id).filter(DrawingSet.id == set_id).scalar()
        return session.query(HVACPath).filter(HVACPath.project_id == project_id).all()
    
    def _match_spaces_by_geometry(self, base_spaces: List[Space], compare_spaces: List[Space]) -> List[GeometricMatch]:
        """Match spaces between sets using simple similarity"""
        matches: List[GeometricMatch] = []
        
        for base_space in base_spaces:
            best_match = None
            best_score = 0.0
            
            for compare_space in compare_spaces:
                score = self._calculate_space_similarity(base_space, compare_space)
                if score > best_score:
                    best_score = score
                    best_match = compare_space
            
            if best_match and best_score > 0:
                geometric_changes = self._detect_space_geometric_changes(base_space, best_match)
                matches.append(GeometricMatch(
                    base_element=base_space,
                    compare_element=best_match,
                    similarity_score=best_score,
                    geometric_changes=geometric_changes,
                ))
        
        return matches
    
    def _match_hvac_by_position(self, base_components: List[HVACComponent], compare_components: List[HVACComponent]) -> List[GeometricMatch]:
        """Match HVAC components by position and type"""
        matches: List[GeometricMatch] = []
        
        for base_comp in base_components:
            best_match = None
            best_score = 0.0
            
            for compare_comp in compare_components:
                if base_comp.component_type == compare_comp.component_type:
                    score = self._calculate_component_similarity(base_comp, compare_comp)
                    if score > best_score:
                        best_score = score
                        best_match = compare_comp
            
            if best_match and best_score > 0:
                geometric_changes = self._detect_component_geometric_changes(base_comp, best_match)
                matches.append(GeometricMatch(
                    base_element=base_comp,
                    compare_element=best_match,
                    similarity_score=best_score,
                    geometric_changes=geometric_changes,
                ))
        
        return matches
    
    def _calculate_space_similarity(self, space1: Space, space2: Space) -> float:
        """Calculate similarity score between two spaces (0-1)"""
        score = 0.0
        
        # Name similarity (30% weight)
        if space1.name and space2.name:
            name_score = 1.0 if space1.name.lower() == space2.name.lower() else 0.0
            score += 0.3 * name_score
        
        # Area similarity (50% weight)
        if space1.floor_area and space2.floor_area:
            area_diff = abs(space1.floor_area - space2.floor_area)
            max_area = max(space1.floor_area, space2.floor_area)
            area_score = max(0.0, 1.0 - (area_diff / max_area))
            score += 0.5 * area_score
        
        # Height similarity (20% weight)
        if space1.ceiling_height and space2.ceiling_height:
            height_diff = abs(space1.ceiling_height - space2.ceiling_height)
            height_score = max(0.0, 1.0 - (height_diff / 20.0))  # 20ft max difference
            score += 0.2 * height_score
        
        return score
    
    def _calculate_component_similarity(self, comp1: HVACComponent, comp2: HVACComponent) -> float:
        """Calculate similarity score between two HVAC components"""
        # Position-based similarity
        if comp1.x_position is not None and comp2.x_position is not None:
            pos_delta = math.sqrt(
                (comp1.x_position - comp2.x_position) ** 2 + (comp1.y_position - comp2.y_position) ** 2
            )
            if pos_delta <= self.POSITION_TOLERANCE:
                return 1.0 - (pos_delta / self.POSITION_TOLERANCE)
        return 0.0
    
    def _detect_space_geometric_changes(self, base_space: Space, compare_space: Space) -> dict:
        """Detect geometric changes between two matched spaces"""
        changes: Dict = {}
        
        # Area changes
        if base_space.floor_area and compare_space.floor_area:
            area_change = compare_space.floor_area - base_space.floor_area
            area_change_pct = (area_change / base_space.floor_area) * 100.0 if base_space.floor_area else 0.0
            if abs(area_change_pct) > 5.0:  # 5% threshold
                changes['area_change'] = {
                    'from': base_space.floor_area,
                    'to': compare_space.floor_area,
                    'delta': area_change,
                    'percent': area_change_pct,
                }
        
        # Height changes
        if base_space.ceiling_height and compare_space.ceiling_height:
            height_change = compare_space.ceiling_height - base_space.ceiling_height
            if abs(height_change) > 0.5:  # 6 inch threshold
                changes['height_change'] = {
                    'from': base_space.ceiling_height,
                    'to': compare_space.ceiling_height,
                    'delta': height_change,
                }
        
        return changes
    
    def _detect_component_geometric_changes(self, base_comp: HVACComponent, compare_comp: HVACComponent) -> dict:
        """Detect geometric changes between two matched HVAC components"""
        changes: Dict = {}
        
        # Position changes
        if base_comp.x_position is not None and compare_comp.x_position is not None:
            pos_delta = math.sqrt(
                (base_comp.x_position - compare_comp.x_position) ** 2 + (base_comp.y_position - compare_comp.y_position) ** 2
            )
            if pos_delta > 10.0:  # 10 pixel threshold
                changes['position_change'] = {
                    'from': {'x': base_comp.x_position, 'y': base_comp.y_position},
                    'to': {'x': compare_comp.x_position, 'y': compare_comp.y_position},
                    'delta': pos_delta,
                }
                changes['position_delta'] = pos_delta
        
        # Noise level changes
        if base_comp.noise_level is not None and compare_comp.noise_level is not None:
            noise_change = compare_comp.noise_level - base_comp.noise_level
            if abs(noise_change) > 1.0:  # 1 dB threshold
                changes['noise_change'] = {
                    'from': base_comp.noise_level,
                    'to': compare_comp.noise_level,
                    'delta': noise_change,
                }
        
        return changes
    
    def _analyze_space_acoustic_impact(self, change_data: dict) -> dict:
        impact = {'impact_score': 0, 'recommendations': []}
        if change_data['change_type'] in ['added', 'removed']:
            impact['impact_score'] = 60
            impact['recommendations'].append('Recalculate RT60 for affected area')
        elif change_data['change_type'] == 'modified':
            area_change = abs(change_data.get('area_change', 0) or 0)
            if area_change > 100.0:
                impact['impact_score'] = 40
                impact['recommendations'].append('Review RT60 calculations due to area change')
        return impact
    
    def _analyze_hvac_acoustic_impact(self, change_data: dict) -> dict:
        impact = {'impact_score': 0, 'recommendations': []}
        if change_data['change_type'] in ['added', 'removed']:
            impact['impact_score'] = 70
            impact['recommendations'].append('Recalculate HVAC noise paths')
        elif change_data['change_type'] == 'modified':
            details = change_data.get('details', {})
            if isinstance(details.get('changes'), dict) and 'noise_change' in details['changes']:
                impact['impact_score'] = 50
                impact['recommendations'].append('Update noise calculations for affected paths')
        return impact
    
    def _analyze_path_acoustic_impact(self, change_data: dict) -> dict:
        impact = {'impact_score': 0, 'recommendations': []}
        if change_data['change_type'] in ['added', 'removed']:
            impact['impact_score'] = 65
            impact['recommendations'].append('Update space noise analysis')
        elif change_data['change_type'] == 'modified':
            impact['impact_score'] = 35
            impact['recommendations'].append('Verify path routing and attenuation')
        return impact