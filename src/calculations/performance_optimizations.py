"""
Performance Optimizations for HVAC Calculations
Implements efficient database queries and reduces unnecessary iterations
"""

from typing import List, Dict, Optional, Any
from sqlalchemy.orm import sessionmaker, scoped_session, joinedload, selectinload
from sqlalchemy import and_, or_

from models.hvac import HVACPath, HVACSegment, HVACComponent
from models.mechanical import MechanicalUnit
from .hvac_constants import MAX_PATH_ELEMENTS


class OptimizedHVACQueryService:
    """Optimized database queries for HVAC operations"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    def get_paths_with_related_data(self, project_id: int) -> List[HVACPath]:
        """
        Get all HVAC paths with eager loading of related entities
        Reduces N+1 query problems by loading everything in one query
        """
        with self.session_factory() as session:
            return session.query(HVACPath).filter(
                HVACPath.project_id == project_id
            ).options(
                # Load all segments with their components in one query
                selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                selectinload(HVACPath.segments).selectinload(HVACSegment.to_component),
                selectinload(HVACPath.segments).selectinload(HVACSegment.fittings),
                # Load primary source and terminal relationships
                joinedload(HVACPath.primary_source),
                joinedload(HVACPath.target_space)
            ).all()
    
    def get_path_with_full_relationships(self, path_id: int) -> Optional[HVACPath]:
        """
        Get a single path with all related data loaded efficiently
        """
        with self.session_factory() as session:
            return session.query(HVACPath).filter(
                HVACPath.id == path_id
            ).options(
                selectinload(HVACPath.segments).selectinload(HVACSegment.from_component),
                selectinload(HVACPath.segments).selectinload(HVACSegment.to_component),
                selectinload(HVACPath.segments).selectinload(HVACSegment.fittings),
                joinedload(HVACPath.primary_source),
                joinedload(HVACPath.target_space)
            ).first()
    
    def get_mechanical_units_by_project(self, project_id: int) -> Dict[str, List[MechanicalUnit]]:
        """
        Get all mechanical units for a project, grouped by type for efficient lookup
        """
        with self.session_factory() as session:
            units = session.query(MechanicalUnit).filter(
                MechanicalUnit.project_id == project_id
            ).all()
            
            # Group by unit type for efficient lookup
            units_by_type = {}
            for unit in units:
                unit_type = (unit.unit_type or 'unknown').lower()
                if unit_type not in units_by_type:
                    units_by_type[unit_type] = []
                units_by_type[unit_type].append(unit)
            
            return units_by_type
    
    def batch_update_segments(self, segment_updates: List[Dict]) -> bool:
        """
        Update multiple segments in a single transaction
        
        Args:
            segment_updates: List of dicts with 'segment_id' and properties to update
        """
        with self.session_factory() as session:
            try:
                # Get all segments to update in one query
                segment_ids = [update['segment_id'] for update in segment_updates]
                segments = session.query(HVACSegment).filter(
                    HVACSegment.id.in_(segment_ids)
                ).all()
                
                # Create lookup for efficient updates
                segments_by_id = {seg.id: seg for seg in segments}
                
                # Apply all updates
                for update in segment_updates:
                    segment_id = update['segment_id']
                    if segment_id in segments_by_id:
                        segment = segments_by_id[segment_id]
                        for key, value in update.items():
                            if key != 'segment_id' and hasattr(segment, key):
                                setattr(segment, key, value)
                
                session.commit()
                return True
                
            except Exception:
                session.rollback()
                return False


class OptimizedDataProcessor:
    """Optimized data processing utilities"""
    
    @staticmethod
    def batch_convert_spectrum_data(spectrum_list: List[List[float]]) -> List[float]:
        """
        Efficiently convert multiple spectrum arrays to dBA values
        Uses vectorized operations where possible
        """
        try:
            import numpy as np
            
            # Convert to numpy array for vectorized operations
            spectra = np.array(spectrum_list)
            
            # A-weighting factors for octave bands
            a_weighting = np.array([-26.2, -16.1, -8.6, -3.2, 0.0, 1.2, 1.0, -1.1])
            
            # Apply A-weighting and convert to linear
            a_weighted = spectra + a_weighting
            linear_levels = 10 ** (a_weighted / 10.0)
            
            # Sum and convert back to dB
            total_linear = np.sum(linear_levels, axis=1)
            dba_levels = 10 * np.log10(total_linear)
            
            return dba_levels.tolist()
            
        except ImportError:
            # Fallback to individual processing if numpy not available
            return [OptimizedDataProcessor._calculate_dba_single(spectrum) for spectrum in spectrum_list]
    
    @staticmethod
    def _calculate_dba_single(spectrum: List[float]) -> float:
        """Calculate dBA for a single spectrum (fallback method)"""
        try:
            if not spectrum or len(spectrum) < 8:
                return 0.0
            
            # A-weighting factors
            a_weighting = [-26.2, -16.1, -8.6, -3.2, 0.0, 1.2, 1.0, -1.1]
            
            # Apply A-weighting and sum
            total_linear = 0.0
            for i, level in enumerate(spectrum[:8]):
                a_weighted_level = level + a_weighting[i]
                total_linear += 10 ** (a_weighted_level / 10.0)
            
            return 10 * math.log10(total_linear) if total_linear > 0 else 0.0
            
        except Exception:
            return 0.0
    
    @staticmethod
    def optimize_path_segment_order(segments: List[HVACSegment]) -> List[HVACSegment]:
        """
        Efficiently order segments by connectivity using optimized algorithm
        Reduces O(n²) to O(n log n) complexity
        """
        if not segments:
            return []
        
        # Create connectivity graph
        connectivity_map = {}
        segments_by_from = {}
        segments_by_to = {}
        
        for segment in segments:
            from_id = getattr(segment.from_component, 'id', None) if segment.from_component else None
            to_id = getattr(segment.to_component, 'id', None) if segment.to_component else None
            
            connectivity_map[segment.id] = {'from': from_id, 'to': to_id, 'segment': segment}
            
            if from_id:
                segments_by_from[from_id] = segment
            if to_id:
                segments_by_to[to_id] = segment
        
        # Find path start (has from_component but no segment leading to it)
        start_candidates = []
        for seg in segments:
            from_id = getattr(seg.from_component, 'id', None) if seg.from_component else None
            if from_id and from_id not in segments_by_to:
                start_candidates.append(seg)
        
        if not start_candidates:
            # Fallback to stored order
            return sorted(segments, key=lambda s: getattr(s, 'segment_order', 0) or 0)
        
        # Build ordered path
        ordered = []
        current = start_candidates[0]
        visited = set()
        
        while current and current.id not in visited:
            ordered.append(current)
            visited.add(current.id)
            
            # Find next segment
            to_id = getattr(current.to_component, 'id', None) if current.to_component else None
            current = segments_by_from.get(to_id) if to_id else None
        
        # Add any remaining segments
        for segment in segments:
            if segment.id not in visited:
                ordered.append(segment)
        
        return ordered


class PerformanceCache:
    """Simple caching system for frequently accessed data"""
    
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.access_order = []
        self.max_size = max_size
    
    def get(self, key: str) -> Any:
        """Get cached value"""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set cached value"""
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # Remove least recently used
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        
        self.cache[key] = value
        self.access_order.append(key)
    
    def clear(self) -> None:
        """Clear all cached values"""
        self.cache.clear()
        self.access_order.clear()


# Global performance cache instance
_performance_cache = PerformanceCache()


def get_performance_cache() -> PerformanceCache:
    """Get the global performance cache instance"""
    return _performance_cache