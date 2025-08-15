# Drawing Sets Comparison Implementation Plan

## Overview
Implement a comprehensive drawing sets comparison system for the Acoustic Analysis Tool to handle different design phases (DD, SD, CD, Final) and compare HVAC designs and room layouts between sets.

## Phase 1: Database Schema Enhancement

### 1.1 New Models (`src/models/drawing_sets.py`)

Create a new model file to define drawing sets and comparison data structures:

#### DrawingSet Model
```python
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class DrawingSet(Base):
    """Drawing set model for grouping drawings by design phase"""
    __tablename__ = 'drawing_sets'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    name = Column(String(255), nullable=False)
    phase_type = Column(String(50), nullable=False)  # 'DD', 'SD', 'CD', 'Final'
    description = Column(Text)
    is_active = Column(Boolean, default=False)  # Current working set
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="drawing_sets")
    drawings = relationship("Drawing", back_populates="drawing_set")
    comparisons_base = relationship("DrawingComparison", 
                                   foreign_keys="DrawingComparison.base_set_id",
                                   back_populates="base_set")
    comparisons_compare = relationship("DrawingComparison", 
                                      foreign_keys="DrawingComparison.compare_set_id",
                                      back_populates="compare_set")
    
    def __repr__(self):
        return f"<DrawingSet(id={self.id}, name='{self.name}', phase='{self.phase_type}')>"
```

#### DrawingComparison Model
```python
class DrawingComparison(Base):
    """Model for storing drawing set comparison results"""
    __tablename__ = 'drawing_comparisons'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    base_set_id = Column(Integer, ForeignKey('drawing_sets.id'), nullable=False)
    compare_set_id = Column(Integer, ForeignKey('drawing_sets.id'), nullable=False)
    comparison_date = Column(DateTime, default=datetime.utcnow)
    comparison_results = Column(Text)  # JSON summary of comparison results
    notes = Column(Text)
    
    # Analysis metadata
    total_changes = Column(Integer, default=0)
    critical_changes = Column(Integer, default=0)
    acoustic_impact_score = Column(Float)  # Overall impact rating 0-100
    
    # Relationships
    project = relationship("Project")
    base_set = relationship("DrawingSet", foreign_keys=[base_set_id], back_populates="comparisons_base")
    compare_set = relationship("DrawingSet", foreign_keys=[compare_set_id], back_populates="comparisons_compare")
    change_items = relationship("ChangeItem", back_populates="comparison", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DrawingComparison(id={self.id}, base_set={self.base_set_id}, compare_set={self.compare_set_id})>"
```

#### ChangeItem Model
```python
class ChangeItem(Base):
    """Model for individual change items detected in comparison"""
    __tablename__ = 'change_items'
    
    id = Column(Integer, primary_key=True)
    comparison_id = Column(Integer, ForeignKey('drawing_comparisons.id'), nullable=False)
    element_type = Column(String(50), nullable=False)  # 'space', 'hvac_component', 'hvac_path', 'room_boundary'
    change_type = Column(String(50), nullable=False)   # 'added', 'removed', 'modified', 'moved'
    
    # Element references (may be null for additions/deletions)
    base_element_id = Column(Integer)  # ID in base set (null for additions)
    compare_element_id = Column(Integer)  # ID in compare set (null for deletions)
    
    # Change details stored as JSON
    change_details = Column(Text)  # Specific changes, coordinates, properties
    acoustic_impact = Column(Text)  # RT60/noise impact analysis JSON
    severity = Column(String(20), default='medium')  # 'low', 'medium', 'high', 'critical'
    
    # Position for UI display
    drawing_id = Column(Integer, ForeignKey('drawings.id'))
    x_position = Column(Float)
    y_position = Column(Float)
    
    # Change metrics
    area_change = Column(Float)  # For space changes, area difference in sq ft
    position_delta = Column(Float)  # Distance moved for repositioned elements
    
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    comparison = relationship("DrawingComparison", back_populates="change_items")
    drawing = relationship("Drawing")
    
    def __repr__(self):
        return f"<ChangeItem(id={self.id}, type='{self.element_type}', change='{self.change_type}')>"
```

### 1.2 Modified Existing Models

#### Drawing Model Enhancement
Add to existing `src/models/drawing.py`:
```python
# Add to existing Drawing model
drawing_set_id = Column(Integer, ForeignKey('drawing_sets.id'), nullable=True)

# Add to relationships section
drawing_set = relationship("DrawingSet", back_populates="drawings")
```

#### Project Model Enhancement
Add to existing `src/models/project.py`:
```python
# Add to relationships section
drawing_sets = relationship("DrawingSet", back_populates="project", cascade="all, delete-orphan")
drawing_comparisons = relationship("DrawingComparison", back_populates="project", cascade="all, delete-orphan")
```

### 1.3 Database Migration (`src/models/migrate_drawing_sets.py`)

Create migration script following the existing pattern:

```python
"""
Database migrations for drawing sets comparison features.

Ensures that legacy databases gain the new tables and columns required for
drawing sets management and comparison functionality.
"""

from typing import List, Tuple
from sqlalchemy import text, Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float
from datetime import datetime
import json

from .database import get_session, Base
from .drawing_sets import DrawingSet, DrawingComparison, ChangeItem


def _get_existing_tables(session) -> List[str]:
    """Get list of existing tables in the database"""
    result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    return [row[0] for row in result.fetchall()]


def _get_existing_columns(session, table_name: str) -> List[str]:
    """Get list of existing columns in a table"""
    result = session.execute(text(f"PRAGMA table_info({table_name})"))
    return [row[1] for row in result.fetchall()]  # column name is at index 1


def _ensure_columns(session, table: str, columns: List[Tuple[str, str]]):
    """
    Ensure the given columns exist on the table.

    Args:
        session: SQLAlchemy session
        table: table name
        columns: list of (column_name, column_sql_type_default_clause)
                 e.g., ("drawing_set_id", "INTEGER")
    """
    existing = set(_get_existing_columns(session, table))
    for name, type_clause in columns:
        if name not in existing:
            session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {type_clause}"))


def _create_default_drawing_sets(session):
    """Create default drawing sets for existing projects with drawings"""
    # Get all projects that have drawings but no drawing sets
    projects_with_drawings = session.execute(text("""
        SELECT DISTINCT p.id, p.name 
        FROM projects p 
        INNER JOIN drawings d ON p.id = d.project_id 
        WHERE p.id NOT IN (SELECT DISTINCT project_id FROM drawing_sets)
    """)).fetchall()
    
    for project_id, project_name in projects_with_drawings:
        # Create a default "Legacy" drawing set for existing drawings
        default_set = DrawingSet(
            project_id=project_id,
            name="Legacy Drawings",
            phase_type="Legacy",
            description="Automatically created for existing drawings",
            is_active=True,
            created_date=datetime.utcnow()
        )
        session.add(default_set)
        session.flush()  # Get the ID
        
        # Assign all unassigned drawings to this set
        session.execute(text("""
            UPDATE drawings 
            SET drawing_set_id = :set_id 
            WHERE project_id = :project_id 
            AND (drawing_set_id IS NULL OR drawing_set_id = 0)
        """), {"set_id": default_set.id, "project_id": project_id})


def ensure_drawing_sets_schema():
    """Run idempotent schema updates for drawing sets functionality."""
    session = get_session()
    try:
        existing_tables = set(_get_existing_tables(session))
        
        # Create new tables if they don't exist
        # This uses SQLAlchemy's create_all which is idempotent
        Base.metadata.create_all(bind=session.get_bind())
        
        # Add drawing_set_id column to existing drawings table
        if 'drawings' in existing_tables:
            _ensure_columns(session, "drawings", [
                ("drawing_set_id", "INTEGER"),
            ])
        
        # Create default drawing sets for existing projects
        # Only if the drawing_sets table exists and has no entries
        if 'drawing_sets' in existing_tables:
            count = session.execute(text("SELECT COUNT(*) FROM drawing_sets")).scalar()
            if count == 0:
                _create_default_drawing_sets(session)
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Drawing sets migration failed: {e}")
        raise
    finally:
        session.close()
```

### 1.4 Update Models Package

Update `src/models/__init__.py`:
```python
# Add new imports
from .drawing_sets import DrawingSet, DrawingComparison, ChangeItem

# Add to __all__ list
__all__ = [
    # ... existing items ...
    'DrawingSet',
    'DrawingComparison',
    'ChangeItem'
]
```

Update `src/models/database.py` to include migration:
```python
def initialize_database(db_path=None):
    # ... existing code ...
    
    # Import all models to ensure they're registered
    from . import project, drawing, space, hvac, rt60_models, mechanical, drawing_sets
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Run migrations
    try:
        from .migrate_hvac_schema import ensure_hvac_schema
        ensure_hvac_schema()
        
        from .migrate_drawing_sets import ensure_drawing_sets_schema
        ensure_drawing_sets_schema()
    except Exception as e:
        print(f"Warning: Schema migration failed: {e}")
```

## Phase 2: Core Comparison Engine

### 2.1 Drawing Comparison Engine (`src/drawing/drawing_comparison.py`)

```python
"""
Drawing comparison engine for detecting changes between drawing sets
"""

import json
import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from models import get_session, DrawingSet, DrawingComparison, ChangeItem, Space, HVACComponent, HVACPath, RoomBoundary
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
        
        Args:
            base_set_id: ID of the base drawing set
            compare_set_id: ID of the compare drawing set
            
        Returns:
            DrawingComparison object with all detected changes
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
                comparison_date=datetime.utcnow()
            )
            session.add(comparison)
            session.flush()  # Get ID
            
            # Collect all changes
            all_changes = []
            
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
                    position_delta=change_data.get('position_delta')
                )
                
                # Analyze acoustic impact
                acoustic_impact = self.analyze_acoustic_impact(change_data)
                change_item.acoustic_impact = json.dumps(acoustic_impact)
                change_item.severity = acoustic_impact.get('severity', 'medium')
                
                if change_item.severity == 'critical':
                    critical_changes += 1
                
                total_acoustic_impact += acoustic_impact.get('impact_score', 0)
                
                session.add(change_item)
            
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
                    'critical_changes': critical_changes
                }
            })
            
            session.commit()
            return comparison
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def detect_space_changes(self, base_spaces: List[Space], compare_spaces: List[Space]) -> List[dict]:
        """Detect changes in room layouts and spaces"""
        changes = []
        
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
                            'compare_area': match.compare_element.floor_area
                        },
                        'drawing_id': match.compare_element.drawing_id,
                        'area_change': (match.compare_element.floor_area or 0) - (match.base_element.floor_area or 0),
                        'position_delta': self._calculate_position_delta(match.base_element, match.compare_element)
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
                        'height': space.ceiling_height
                    },
                    'drawing_id': space.drawing_id,
                    'area_change': space.floor_area or 0
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
                        'height': space.ceiling_height
                    },
                    'drawing_id': space.drawing_id,
                    'area_change': -(space.floor_area or 0)
                })
        
        return changes
    
    def detect_hvac_changes(self, base_components: List[HVACComponent], compare_components: List[HVACComponent]) -> List[dict]:
        """Detect changes in HVAC components"""
        changes = []
        
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
                            'changes': match.geometric_changes
                        },
                        'drawing_id': match.compare_element.drawing_id,
                        'x_position': match.compare_element.x_position,
                        'y_position': match.compare_element.y_position,
                        'position_delta': match.geometric_changes.get('position_delta', 0)
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
                        'noise_level': component.noise_level
                    },
                    'drawing_id': component.drawing_id,
                    'x_position': component.x_position,
                    'y_position': component.y_position
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
                        'noise_level': component.noise_level
                    },
                    'drawing_id': component.drawing_id,
                    'x_position': component.x_position,
                    'y_position': component.y_position
                })
        
        return changes
    
    def detect_path_changes(self, base_paths: List[HVACPath], compare_paths: List[HVACPath]) -> List[dict]:
        """Detect changes in HVAC paths"""
        changes = []
        
        # Simple name-based matching for paths (could be enhanced with routing analysis)
        base_path_names = {path.name: path for path in base_paths}
        compare_path_names = {path.name: path for path in compare_paths}
        
        # Find modifications
        for name in base_path_names.keys() & compare_path_names.keys():
            base_path = base_path_names[name]
            compare_path = compare_path_names[name]
            
            path_changes = {}
            
            # Check for target space changes
            if base_path.target_space_id != compare_path.target_space_id:
                path_changes['target_space_changed'] = True
            
            # Check for segment count changes
            base_segments = len(base_path.segments) if base_path.segments else 0
            compare_segments = len(compare_path.segments) if compare_path.segments else 0
            if base_segments != compare_segments:
                path_changes['segment_count_changed'] = {
                    'from': base_segments,
                    'to': compare_segments
                }
            
            if path_changes:
                changes.append({
                    'element_type': 'hvac_path',
                    'change_type': 'modified',
                    'base_element_id': base_path.id,
                    'compare_element_id': compare_path.id,
                    'details': {
                        'name': name,
                        'path_type': compare_path.path_type,
                        'changes': path_changes
                    }
                })
        
        # Find additions
        for name in compare_path_names.keys() - base_path_names.keys():
            path = compare_path_names[name]
            changes.append({
                'element_type': 'hvac_path',
                'change_type': 'added',
                'compare_element_id': path.id,
                'details': {
                    'name': name,
                    'path_type': path.path_type,
                    'target_space_id': path.target_space_id
                }
            })
        
        # Find removals
        for name in base_path_names.keys() - compare_path_names.keys():
            path = base_path_names[name]
            changes.append({
                'element_type': 'hvac_path',
                'change_type': 'removed',
                'base_element_id': path.id,
                'details': {
                    'name': name,
                    'path_type': path.path_type,
                    'target_space_id': path.target_space_id
                }
            })
        
        return changes
    
    def analyze_acoustic_impact(self, change_data: dict) -> dict:
        """Analyze acoustic impact of detected changes"""
        impact = {
            'impact_score': 0,  # 0-100 scale
            'severity': 'low',
            'rt60_impact': None,
            'noise_impact': None,
            'recommendations': []
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
        return session.query(Space).join(Drawing).filter(Drawing.drawing_set_id == set_id).all()
    
    def _get_hvac_components_for_set(self, session, set_id: int) -> List[HVACComponent]:
        """Get all HVAC components associated with drawings in a set"""
        return session.query(HVACComponent).join(Drawing).filter(Drawing.drawing_set_id == set_id).all()
    
    def _get_hvac_paths_for_set(self, session, set_id: int) -> List[HVACPath]:
        """Get all HVAC paths associated with a drawing set"""
        # This is more complex as paths are project-level but need to be associated with sets
        # For now, get all paths for the project and filter based on component locations
        project_id = session.query(DrawingSet.project_id).filter(DrawingSet.id == set_id).scalar()
        return session.query(HVACPath).filter(HVACPath.project_id == project_id).all()
    
    def _match_spaces_by_geometry(self, base_spaces: List[Space], compare_spaces: List[Space]) -> List[GeometricMatch]:
        """Match spaces between sets using geometric similarity"""
        matches = []
        
        for base_space in base_spaces:
            best_match = None
            best_score = 0
            
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
                    geometric_changes=geometric_changes
                ))
        
        return matches
    
    def _match_hvac_by_position(self, base_components: List[HVACComponent], compare_components: List[HVACComponent]) -> List[GeometricMatch]:
        """Match HVAC components by position and type"""
        matches = []
        
        for base_comp in base_components:
            best_match = None
            best_score = 0
            
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
                    geometric_changes=geometric_changes
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
            area_score = max(0, 1 - (area_diff / max_area))
            score += 0.5 * area_score
        
        # Height similarity (20% weight)
        if space1.ceiling_height and space2.ceiling_height:
            height_diff = abs(space1.ceiling_height - space2.ceiling_height)
            height_score = max(0, 1 - (height_diff / 20))  # 20ft max difference
            score += 0.2 * height_score
        
        return score
    
    def _calculate_component_similarity(self, comp1: HVACComponent, comp2: HVACComponent) -> float:
        """Calculate similarity score between two HVAC components"""
        # Position-based similarity
        if comp1.x_position is not None and comp2.x_position is not None:
            pos_delta = math.sqrt(
                (comp1.x_position - comp2.x_position) ** 2 +
                (comp1.y_position - comp2.y_position) ** 2
            )
            
            # Score decreases with distance, 0 at POSITION_TOLERANCE
            if pos_delta <= self.POSITION_TOLERANCE:
                return 1.0 - (pos_delta / self.POSITION_TOLERANCE)
        
        return 0.0
    
    def _detect_space_geometric_changes(self, base_space: Space, compare_space: Space) -> dict:
        """Detect geometric changes between two matched spaces"""
        changes = {}
        
        # Area changes
        if base_space.floor_area and compare_space.floor_area:
            area_change = compare_space.floor_area - base_space.floor_area
            area_change_pct = (area_change / base_space.floor_area) * 100
            if abs(area_change_pct) > 5:  # 5% threshold
                changes['area_change'] = {
                    'from': base_space.floor_area,
                    'to': compare_space.floor_area,
                    'delta': area_change,
                    'percent': area_change_pct
                }
        
        # Height changes
        if base_space.ceiling_height and compare_space.ceiling_height:
            height_change = compare_space.ceiling_height - base_space.ceiling_height
            if abs(height_change) > 0.5:  # 6 inch threshold
                changes['height_change'] = {
                    'from': base_space.ceiling_height,
                    'to': compare_space.ceiling_height,
                    'delta': height_change
                }
        
        return changes
    
    def _detect_component_geometric_changes(self, base_comp: HVACComponent, compare_comp: HVACComponent) -> dict:
        """Detect geometric changes between two matched HVAC components"""
        changes = {}
        
        # Position changes
        if (base_comp.x_position is not None and compare_comp.x_position is not None):
            pos_delta = math.sqrt(
                (base_comp.x_position - compare_comp.x_position) ** 2 +
                (base_comp.y_position - compare_comp.y_position) ** 2
            )
            
            if pos_delta > 10:  # 10 pixel threshold
                changes['position_change'] = {
                    'from': {'x': base_comp.x_position, 'y': base_comp.y_position},
                    'to': {'x': compare_comp.x_position, 'y': compare_comp.y_position},
                    'delta': pos_delta
                }
                changes['position_delta'] = pos_delta
        
        # Noise level changes
        if (base_comp.noise_level is not None and compare_comp.noise_level is not None):
            noise_change = compare_comp.noise_level - base_comp.noise_level
            if abs(noise_change) > 1:  # 1 dB threshold
                changes['noise_change'] = {
                    'from': base_comp.noise_level,
                    'to': compare_comp.noise_level,
                    'delta': noise_change
                }
        
        return changes
    
    def _calculate_position_delta(self, element1, element2) -> float:
        """Calculate position delta between two elements"""
        # This is a simplified version - would need to be implemented based on element type
        return 0.0
    
    def _analyze_space_acoustic_impact(self, change_data: dict) -> dict:
        """Analyze acoustic impact of space changes"""
        impact = {'impact_score': 0, 'recommendations': []}
        
        if change_data['change_type'] in ['added', 'removed']:
            impact['impact_score'] = 60  # Major change
            impact['recommendations'].append('Recalculate RT60 for affected area')
        elif change_data['change_type'] == 'modified':
            area_change = abs(change_data.get('area_change', 0))
            if area_change > 100:  # More than 100 sq ft change
                impact['impact_score'] = 40
                impact['recommendations'].append('Review RT60 calculations due to area change')
        
        return impact
    
    def _analyze_hvac_acoustic_impact(self, change_data: dict) -> dict:
        """Analyze acoustic impact of HVAC component changes"""
        impact = {'impact_score': 0, 'recommendations': []}
        
        if change_data['change_type'] in ['added', 'removed']:
            impact['impact_score'] = 70  # Major HVAC change
            impact['recommendations'].append('Recalculate HVAC noise paths')
        elif change_data['change_type'] == 'modified':
            # Check for position or noise level changes
            details = change_data.get('details', {})
            if 'noise_change' in details.get('changes', {}):
                impact['impact_score'] = 50
                impact['recommendations'].append('Update noise calculations for affected paths')
        
        return impact
    
    def _analyze_path_acoustic_impact(self, change_data: dict) -> dict:
        """Analyze acoustic impact of HVAC path changes"""
        impact = {'impact_score': 0, 'recommendations': []}
        
        if change_data['change_type'] in ['added', 'removed']:
            impact['impact_score'] = 65
            impact['recommendations'].append('Update space noise analysis')
        elif change_data['change_type'] == 'modified':
            impact['impact_score'] = 35
            impact['recommendations'].append('Verify path routing and attenuation')
        
        return impact
```

### 2.2 Change Detection Utilities (`src/drawing/change_detector.py`)

```python
"""
Spatial change detection utilities for drawing comparison
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from models import Space, RoomBoundary, HVACComponent


@dataclass
class SpatialBounds:
    """Represents spatial bounds of an element"""
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)
    
    @property
    def area(self) -> float:
        return (self.x_max - self.x_min) * (self.y_max - self.y_min)
    
    def overlaps_with(self, other: 'SpatialBounds') -> float:
        """Calculate overlap area with another bounds"""
        overlap_x = max(0, min(self.x_max, other.x_max) - max(self.x_min, other.x_min))
        overlap_y = max(0, min(self.y_max, other.y_max) - max(self.y_min, other.y_min))
        return overlap_x * overlap_y


class SpatialChangeDetector:
    """Advanced spatial analysis for detecting geometric changes"""
    
    def __init__(self):
        self.overlap_threshold = 0.5  # 50% overlap for matching
        self.position_tolerance = 25.0  # pixels
    
    def match_spaces_by_geometry(self, base_spaces: List[Space], compare_spaces: List[Space]) -> Dict[int, Dict]:
        """
        Match spaces between sets using advanced spatial overlap analysis
        
        Returns:
            Dict mapping base_space_id to match info: {compare_space_id, confidence, changes}
        """
        matches = {}
        
        # Get spatial bounds for all spaces
        base_bounds = {}
        compare_bounds = {}
        
        for space in base_spaces:
            bounds = self._get_space_bounds(space)
            if bounds:
                base_bounds[space.id] = bounds
        
        for space in compare_spaces:
            bounds = self._get_space_bounds(space)
            if bounds:
                compare_bounds[space.id] = bounds
        
        # Calculate overlap matrix
        used_compare_spaces = set()
        
        for base_id, base_bound in base_bounds.items():
            best_match = None
            best_confidence = 0
            
            for compare_id, compare_bound in compare_bounds.items():
                if compare_id in used_compare_spaces:
                    continue
                
                # Calculate spatial similarity
                overlap_area = base_bound.overlaps_with(compare_bound)
                union_area = base_bound.area + compare_bound.area - overlap_area
                
                if union_area > 0:
                    overlap_ratio = overlap_area / union_area
                    
                    # Additional factors: center distance, area ratio
                    center_distance = self._calculate_distance(base_bound.center, compare_bound.center)
                    area_ratio = min(base_bound.area, compare_bound.area) / max(base_bound.area, compare_bound.area)
                    
                    # Combined confidence score
                    confidence = (
                        0.6 * overlap_ratio +
                        0.2 * max(0, 1 - center_distance / 200) +  # Distance penalty
                        0.2 * area_ratio
                    )
                    
                    if confidence > best_confidence and confidence > self.overlap_threshold:
                        best_confidence = confidence
                        best_match = compare_id
            
            if best_match:
                matches[base_id] = {
                    'compare_space_id': best_match,
                    'confidence': best_confidence,
                    'changes': self._detect_boundary_changes(base_bounds[base_id], compare_bounds[best_match])
                }
                used_compare_spaces.add(best_match)
        
        return matches
    
    def detect_boundary_changes(self, base_boundaries: List[RoomBoundary], compare_boundaries: List[RoomBoundary]) -> List[Dict]:
        """Detect specific room boundary modifications"""
        changes = []
        
        # Group boundaries by space
        base_by_space = {}
        compare_by_space = {}
        
        for boundary in base_boundaries:
            if boundary.space_id not in base_by_space:
                base_by_space[boundary.space_id] = []
            base_by_space[boundary.space_id].append(boundary)
        
        for boundary in compare_boundaries:
            if boundary.space_id not in compare_by_space:
                compare_by_space[boundary.space_id] = []
            compare_by_space[boundary.space_id].append(boundary)
        
        # Compare boundaries for each space
        for space_id in base_by_space.keys() | compare_by_space.keys():
            base_bounds = base_by_space.get(space_id, [])
            compare_bounds = compare_by_space.get(space_id, [])
            
            if not base_bounds:
                # New boundaries added
                changes.append({
                    'type': 'boundaries_added',
                    'space_id': space_id,
                    'count': len(compare_bounds)
                })
            elif not compare_bounds:
                # Boundaries removed
                changes.append({
                    'type': 'boundaries_removed',
                    'space_id': space_id,
                    'count': len(base_bounds)
                })
            else:
                # Check for modifications
                boundary_changes = self._compare_boundary_sets(base_bounds, compare_bounds)
                if boundary_changes:
                    changes.append({
                        'type': 'boundaries_modified',
                        'space_id': space_id,
                        'changes': boundary_changes
                    })
        
        return changes
    
    def classify_hvac_changes(self, base_component: HVACComponent, compare_component: HVACComponent) -> Dict:
        """Classify types of HVAC component changes with spatial context"""
        changes = {}
        
        # Position changes
        if (base_component.x_position is not None and compare_component.x_position is not None):
            distance = self._calculate_distance(
                (base_component.x_position, base_component.y_position),
                (compare_component.x_position, compare_component.y_position)
            )
            
            if distance > self.position_tolerance:
                changes['position'] = {
                    'moved_distance': distance,
                    'from': (base_component.x_position, base_component.y_position),
                    'to': (compare_component.x_position, compare_component.y_position)
                }
                
                # Classify movement type
                if distance > 200:
                    changes['movement_type'] = 'major_relocation'
                elif distance > 100:
                    changes['movement_type'] = 'significant_move'
                else:
                    changes['movement_type'] = 'minor_adjustment'
        
        # Type changes
        if base_component.component_type != compare_component.component_type:
            changes['type_change'] = {
                'from': base_component.component_type,
                'to': compare_component.component_type
            }
        
        # Noise level changes
        if (base_component.noise_level is not None and compare_component.noise_level is not None):
            noise_delta = compare_component.noise_level - base_component.noise_level
            if abs(noise_delta) > 1:  # 1 dB threshold
                changes['noise_level'] = {
                    'from': base_component.noise_level,
                    'to': compare_component.noise_level,
                    'delta': noise_delta
                }
        
        return changes
    
    def _get_space_bounds(self, space: Space) -> Optional[SpatialBounds]:
        """Calculate spatial bounds for a space based on its room boundaries"""
        if not space.room_boundaries:
            return None
        
        x_coords = []
        y_coords = []
        
        for boundary in space.room_boundaries:
            x_coords.extend([boundary.x1, boundary.x2])
            y_coords.extend([boundary.y1, boundary.y2])
        
        if x_coords and y_coords:
            return SpatialBounds(
                x_min=min(x_coords),
                y_min=min(y_coords),
                x_max=max(x_coords),
                y_max=max(y_coords)
            )
        
        return None
    
    def _calculate_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points"""
        return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)
    
    def _compare_boundary_sets(self, base_boundaries: List[RoomBoundary], compare_boundaries: List[RoomBoundary]) -> Dict:
        """Compare two sets of room boundaries for changes"""
        changes = {}
        
        # Simple comparison based on count and total perimeter
        base_perimeter = sum(self._calculate_boundary_length(b) for b in base_boundaries)
        compare_perimeter = sum(self._calculate_boundary_length(b) for b in compare_boundaries)
        
        perimeter_change = compare_perimeter - base_perimeter
        if abs(perimeter_change) > 5:  # 5 unit threshold
            changes['perimeter_change'] = {
                'from': base_perimeter,
                'to': compare_perimeter,
                'delta': perimeter_change
            }
        
        count_change = len(compare_boundaries) - len(base_boundaries)
        if count_change != 0:
            changes['boundary_count_change'] = {
                'from': len(base_boundaries),
                'to': len(compare_boundaries),
                'delta': count_change
            }
        
        return changes
    
    def _calculate_boundary_length(self, boundary: RoomBoundary) -> float:
        """Calculate length of a room boundary"""
        return math.sqrt((boundary.x2 - boundary.x1) ** 2 + (boundary.y2 - boundary.y1) ** 2)
```

## Phase 3: Project Dashboard Enhancement

### 3.1 Add Drawing Sets Tab to Project Dashboard

Update `src/ui/project_dashboard.py`:

```python
# Add to imports
from ui.dialogs.drawing_sets_dialog import DrawingSetsDialog
from ui.drawing_comparison_interface import DrawingComparisonInterface
from models import DrawingSet, DrawingComparison

# Add to create_left_panel method
def create_left_panel(self):
    """Create the left panel with project elements"""
    left_widget = QWidget()
    left_layout = QVBoxLayout()
    
    # Create tabs for different element types
    tabs = QTabWidget()
    
    # Drawing Sets tab (NEW)
    drawing_sets_tab = self.create_drawing_sets_tab()
    tabs.addTab(drawing_sets_tab, "📁 Drawing Sets")
    
    # Enhanced Drawings tab
    drawings_tab = self.create_drawings_tab()
    tabs.addTab(drawings_tab, "Drawings")
    
    # ... existing tabs ...
    
    left_layout.addWidget(tabs)
    left_widget.setLayout(left_layout)
    
    return left_widget

# Add new method
def create_drawing_sets_tab(self):
    """Create the drawing sets management tab"""
    widget = QWidget()
    layout = QVBoxLayout()
    
    # Drawing sets list with phase indicators
    self.drawing_sets_list = QListWidget()
    self.apply_dark_list_style(self.drawing_sets_list)
    self.drawing_sets_list.itemDoubleClicked.connect(self.manage_drawing_sets)
    layout.addWidget(self.drawing_sets_list)
    
    # Management buttons
    button_layout = QHBoxLayout()
    
    new_set_btn = QPushButton("New Set")
    new_set_btn.clicked.connect(self.create_new_drawing_set)
    
    set_active_btn = QPushButton("Set Active")
    set_active_btn.clicked.connect(self.set_active_drawing_set)
    
    compare_sets_btn = QPushButton("Compare Sets")
    compare_sets_btn.clicked.connect(self.compare_drawing_sets)
    
    manage_sets_btn = QPushButton("Manage Sets")
    manage_sets_btn.clicked.connect(self.manage_drawing_sets)
    
    button_layout.addWidget(new_set_btn)
    button_layout.addWidget(set_active_btn)
    button_layout.addWidget(compare_sets_btn)
    button_layout.addWidget(manage_sets_btn)
    button_layout.addStretch()
    
    layout.addLayout(button_layout)
    widget.setLayout(layout)
    
    return widget

# Add new refresh method
def refresh_drawing_sets(self):
    """Refresh the drawing sets list"""
    try:
        session = get_session()
        drawing_sets = session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).order_by(DrawingSet.created_date).all()
        
        self.drawing_sets_list.clear()
        for drawing_set in drawing_sets:
            # Count drawings in set
            drawing_count = len(drawing_set.drawings) if drawing_set.drawings else 0
            
            # Active indicator
            active_indicator = "🟢" if drawing_set.is_active else "⚪"
            
            # Phase color coding
            phase_colors = {
                'DD': '🟦',  # Blue for Design Development
                'SD': '🟨',  # Yellow for Schematic Design
                'CD': '🟥',  # Red for Construction Documents
                'Final': '🟩',  # Green for Final
                'Legacy': '⚫'  # Black for Legacy
            }
            phase_icon = phase_colors.get(drawing_set.phase_type, '⚪')
            
            item_text = f"{active_indicator} {phase_icon} {drawing_set.name} ({drawing_set.phase_type}) - {drawing_count} drawings"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, drawing_set.id)
            
            # Color coding for active sets
            if drawing_set.is_active:
                item.setForeground(QColor(144, 238, 144))  # Light green for active
            
            self.drawing_sets_list.addItem(item)
        
        session.close()
        
    except Exception as e:
        QMessageBox.warning(self, "Warning", f"Could not load drawing sets:\n{str(e)}")

# Update refresh_all_data method
def refresh_all_data(self):
    """Refresh all data displays"""
    self.refresh_drawing_sets()  # Add this line
    self.refresh_drawings()
    self.refresh_spaces()
    self.refresh_hvac_paths()
    self.refresh_component_library()
    self.update_analysis_status()
    self.update_status_bar()
    
    # Refresh results widget
    if hasattr(self, 'results_widget'):
        self.results_widget.refresh_data()

# Enhanced refresh_drawings method
def refresh_drawings(self):
    """Refresh drawings list grouped by drawing sets"""
    try:
        session = get_session()
        
        # Get all drawing sets for this project
        drawing_sets = session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).order_by(DrawingSet.created_date).all()
        
        # Get unassigned drawings (no drawing set)
        unassigned_drawings = session.query(Drawing).filter(
            Drawing.project_id == self.project_id,
            Drawing.drawing_set_id.is_(None)
        ).all()
        
        self.drawings_list.clear()
        
        # Add drawings grouped by sets
        for drawing_set in drawing_sets:
            if drawing_set.drawings:  # Only show sets with drawings
                # Add set header
                active_indicator = "🟢" if drawing_set.is_active else ""
                set_header_text = f"📁 {drawing_set.name} ({drawing_set.phase_type}) {active_indicator}"
                set_header = QListWidgetItem(set_header_text)
                set_header.setData(Qt.UserRole, {'type': 'set', 'id': drawing_set.id})
                
                # Style set headers differently
                font = QFont()
                font.setBold(True)
                set_header.setFont(font)
                if drawing_set.is_active:
                    set_header.setForeground(QColor(144, 238, 144))
                
                self.drawings_list.addItem(set_header)
                
                # Add drawings under set
                for drawing in drawing_set.drawings:
                    drawing_item_text = f"  📄 {drawing.name}"
                    drawing_item = QListWidgetItem(drawing_item_text)
                    drawing_item.setData(Qt.UserRole, {'type': 'drawing', 'id': drawing.id})
                    self.drawings_list.addItem(drawing_item)
        
        # Add unassigned drawings
        if unassigned_drawings:
            unassigned_header = QListWidgetItem("📁 Unassigned Drawings")
            unassigned_header.setData(Qt.UserRole, {'type': 'unassigned'})
            font = QFont()
            font.setBold(True)
            font.setItalic(True)
            unassigned_header.setFont(font)
            unassigned_header.setForeground(QColor(255, 215, 0))  # Gold for unassigned
            self.drawings_list.addItem(unassigned_header)
            
            for drawing in unassigned_drawings:
                drawing_item_text = f"  📄 {drawing.name}"
                drawing_item = QListWidgetItem(drawing_item_text)
                drawing_item.setData(Qt.UserRole, {'type': 'drawing', 'id': drawing.id})
                self.drawings_list.addItem(drawing_item)
        
        session.close()
        
    except Exception as e:
        QMessageBox.warning(self, "Warning", f"Could not load drawings:\n{str(e)}")

# Add new methods for drawing sets management
def create_new_drawing_set(self):
    """Create a new drawing set"""
    try:
        dialog = DrawingSetsDialog(self, self.project_id, mode='create')
        if dialog.exec() == QDialog.Accepted:
            self.refresh_drawing_sets()
            self.refresh_drawings()
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to create drawing set:\n{str(e)}")

def set_active_drawing_set(self):
    """Set the selected drawing set as active"""
    try:
        current_item = self.drawing_sets_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Set Active", "Please select a drawing set.")
            return
        
        set_id = current_item.data(Qt.UserRole)
        
        session = get_session()
        
        # Deactivate all sets for this project
        session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).update({DrawingSet.is_active: False})
        
        # Activate selected set
        drawing_set = session.query(DrawingSet).filter(DrawingSet.id == set_id).first()
        if drawing_set:
            drawing_set.is_active = True
            session.commit()
            
            QMessageBox.information(self, "Active Set", f"'{drawing_set.name}' is now the active drawing set.")
            self.refresh_drawing_sets()
        
        session.close()
        
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to set active drawing set:\n{str(e)}")

def compare_drawing_sets(self):
    """Open drawing sets comparison interface"""
    try:
        # Get available drawing sets
        session = get_session()
        drawing_sets = session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).all()
        session.close()
        
        if len(drawing_sets) < 2:
            QMessageBox.information(self, "Compare Sets", "At least two drawing sets are required for comparison.")
            return
        
        # Show selection dialog
        from ui.dialogs.comparison_selection_dialog import ComparisonSelectionDialog
        dialog = ComparisonSelectionDialog(self, drawing_sets)
        if dialog.exec() == QDialog.Accepted:
            base_set_id, compare_set_id = dialog.get_selected_sets()
            
            # Open comparison interface
            comparison_interface = DrawingComparisonInterface(base_set_id, compare_set_id)
            comparison_interface.show()
            
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to open comparison:\n{str(e)}")

def manage_drawing_sets(self):
    """Open drawing sets management dialog"""
    try:
        dialog = DrawingSetsDialog(self, self.project_id, mode='manage')
        if dialog.exec() == QDialog.Accepted:
            self.refresh_drawing_sets()
            self.refresh_drawings()
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to open drawing sets management:\n{str(e)}")
```

## Phase 4: New UI Components

### 4.1 Drawing Sets Management Dialog (`src/ui/dialogs/drawing_sets_dialog.py`)

```python
"""
Drawing Sets Management Dialog
Handles creation, editing, and assignment of drawings to sets
"""

import json
from typing import List, Optional
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QListWidget, QListWidgetItem, QLineEdit, QComboBox, 
                               QTextEdit, QGroupBox, QSplitter, QMessageBox, QCheckBox,
                               QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDrag

from models import get_session, DrawingSet, Drawing, Project


class DrawingSetsDialog(QDialog):
    """Dialog for managing drawing sets and assignments"""
    
    def __init__(self, parent, project_id: int, mode: str = 'manage'):
        super().__init__(parent)
        self.project_id = project_id
        self.mode = mode  # 'create', 'edit', 'manage'
        self.project = None
        self.drawing_sets = []
        self.drawings = []
        
        self.load_data()
        self.init_ui()
        self.refresh_data()
    
    def load_data(self):
        """Load project data"""
        session = get_session()
        try:
            self.project = session.query(Project).filter(Project.id == self.project_id).first()
            self.drawing_sets = session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).all()
            self.drawings = session.query(Drawing).filter(Drawing.project_id == self.project_id).all()
        finally:
            session.close()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"Drawing Sets Management - {self.project.name if self.project else 'Project'}")
        self.setGeometry(200, 200, 900, 700)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        if self.mode == 'create':
            self.create_creation_ui(layout)
        else:
            self.create_management_ui(layout)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_creation_ui(self, layout):
        """Create UI for creating a new drawing set"""
        # Set properties
        properties_group = QGroupBox("New Drawing Set Properties")
        properties_layout = QVBoxLayout()
        
        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        properties_layout.addLayout(name_layout)
        
        # Phase type
        phase_layout = QHBoxLayout()
        phase_layout.addWidget(QLabel("Phase:"))
        self.phase_combo = QComboBox()
        self.phase_combo.addItems(['DD', 'SD', 'CD', 'Final', 'Other'])
        phase_layout.addWidget(self.phase_combo)
        properties_layout.addLayout(phase_layout)
        
        # Description
        properties_layout.addWidget(QLabel("Description:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        properties_layout.addWidget(self.description_edit)
        
        # Set as active
        self.active_checkbox = QCheckBox("Set as active drawing set")
        properties_layout.addWidget(self.active_checkbox)
        
        properties_group.setLayout(properties_layout)
        layout.addWidget(properties_group)
    
    def create_management_ui(self, layout):
        """Create UI for managing existing drawing sets"""
        # Create tabs
        tabs = QTabWidget()
        
        # Drawing Sets tab
        sets_tab = self.create_sets_tab()
        tabs.addTab(sets_tab, "Drawing Sets")
        
        # Assignment tab
        assignment_tab = self.create_assignment_tab()
        tabs.addTab(assignment_tab, "Drawing Assignment")
        
        layout.addWidget(tabs)
    
    def create_sets_tab(self):
        """Create the drawing sets management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Drawing sets list
        sets_group = QGroupBox("Drawing Sets")
        sets_layout = QVBoxLayout()
        
        self.sets_table = QTableWidget()
        self.sets_table.setColumnCount(5)
        self.sets_table.setHorizontalHeaderLabels(['Name', 'Phase', 'Drawings', 'Active', 'Created'])
        self.sets_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Configure table
        header = self.sets_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Name column
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        sets_layout.addWidget(self.sets_table)
        
        # Sets buttons
        sets_button_layout = QHBoxLayout()
        
        new_set_btn = QPushButton("New Set")
        new_set_btn.clicked.connect(self.create_new_set)
        
        edit_set_btn = QPushButton("Edit Set")
        edit_set_btn.clicked.connect(self.edit_selected_set)
        
        delete_set_btn = QPushButton("Delete Set")
        delete_set_btn.clicked.connect(self.delete_selected_set)
        
        set_active_btn = QPushButton("Set Active")
        set_active_btn.clicked.connect(self.set_selected_active)
        
        sets_button_layout.addWidget(new_set_btn)
        sets_button_layout.addWidget(edit_set_btn)
        sets_button_layout.addWidget(delete_set_btn)
        sets_button_layout.addWidget(set_active_btn)
        sets_button_layout.addStretch()
        
        sets_layout.addLayout(sets_button_layout)
        sets_group.setLayout(sets_layout)
        layout.addWidget(sets_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_assignment_tab(self):
        """Create the drawing assignment tab with drag-and-drop"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Drag drawings between sets to reassign them. Double-click to edit drawing properties.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Splitter for drawing sets and unassigned drawings
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Drawing sets
        sets_widget = QWidget()
        sets_layout = QVBoxLayout()
        sets_layout.addWidget(QLabel("Drawing Sets:"))
        
        self.assignment_sets_list = QListWidget()
        self.assignment_sets_list.setDragDropMode(QListWidget.DragDrop)
        self.assignment_sets_list.setDefaultDropAction(Qt.MoveAction)
        sets_layout.addWidget(self.assignment_sets_list)
        
        sets_widget.setLayout(sets_layout)
        splitter.addWidget(sets_widget)
        
        # Right side: Individual drawings
        drawings_widget = QWidget()
        drawings_layout = QVBoxLayout()
        drawings_layout.addWidget(QLabel("All Drawings:"))
        
        self.assignment_drawings_list = QListWidget()
        self.assignment_drawings_list.setDragDropMode(QListWidget.DragDrop)
        self.assignment_drawings_list.setDefaultDropAction(Qt.MoveAction)
        drawings_layout.addWidget(self.assignment_drawings_list)
        
        drawings_widget.setLayout(drawings_layout)
        splitter.addWidget(drawings_widget)
        
        layout.addWidget(splitter)
        widget.setLayout(layout)
        return widget
    
    def refresh_data(self):
        """Refresh all data displays"""
        self.load_data()  # Reload from database
        
        if hasattr(self, 'sets_table'):
            self.refresh_sets_table()
        
        if hasattr(self, 'assignment_sets_list'):
            self.refresh_assignment_lists()
    
    def refresh_sets_table(self):
        """Refresh the drawing sets table"""
        self.sets_table.setRowCount(len(self.drawing_sets))
        
        for row, drawing_set in enumerate(self.drawing_sets):
            # Name
            name_item = QTableWidgetItem(drawing_set.name)
            name_item.setData(Qt.UserRole, drawing_set.id)
            self.sets_table.setItem(row, 0, name_item)
            
            # Phase
            phase_item = QTableWidgetItem(drawing_set.phase_type)
            self.sets_table.setItem(row, 1, phase_item)
            
            # Drawing count
            drawing_count = len(drawing_set.drawings) if drawing_set.drawings else 0
            count_item = QTableWidgetItem(str(drawing_count))
            self.sets_table.setItem(row, 2, count_item)
            
            # Active status
            active_item = QTableWidgetItem("Yes" if drawing_set.is_active else "No")
            self.sets_table.setItem(row, 3, active_item)
            
            # Created date
            created_item = QTableWidgetItem(drawing_set.created_date.strftime("%Y-%m-%d"))
            self.sets_table.setItem(row, 4, created_item)
    
    def refresh_assignment_lists(self):
        """Refresh the assignment lists"""
        # Clear lists
        self.assignment_sets_list.clear()
        self.assignment_drawings_list.clear()
        
        # Add drawing sets with their drawings
        for drawing_set in self.drawing_sets:
            # Add set header
            set_item = QListWidgetItem(f"📁 {drawing_set.name} ({drawing_set.phase_type})")
            set_item.setData(Qt.UserRole, {'type': 'set', 'id': drawing_set.id})
            self.assignment_sets_list.addItem(set_item)
            
            # Add drawings in set
            if drawing_set.drawings:
                for drawing in drawing_set.drawings:
                    drawing_item = QListWidgetItem(f"  📄 {drawing.name}")
                    drawing_item.setData(Qt.UserRole, {'type': 'drawing', 'id': drawing.id, 'set_id': drawing_set.id})
                    self.assignment_sets_list.addItem(drawing_item)
        
        # Add all drawings to the drawings list for reference
        for drawing in self.drawings:
            set_name = "Unassigned"
            if drawing.drawing_set_id:
                drawing_set = next((ds for ds in self.drawing_sets if ds.id == drawing.drawing_set_id), None)
                if drawing_set:
                    set_name = f"{drawing_set.name} ({drawing_set.phase_type})"
            
            drawing_item = QListWidgetItem(f"📄 {drawing.name} - {set_name}")
            drawing_item.setData(Qt.UserRole, {'type': 'drawing', 'id': drawing.id, 'set_id': drawing.drawing_set_id})
            self.assignment_drawings_list.addItem(drawing_item)
    
    def create_new_set(self):
        """Create a new drawing set"""
        try:
            # Create a simple input dialog for new set
            from PySide6.QtWidgets import QInputDialog
            
            name, ok = QInputDialog.getText(self, "New Drawing Set", "Enter set name:")
            if not ok or not name.strip():
                return
            
            phase, ok = QInputDialog.getItem(self, "Drawing Set Phase", "Select phase:", 
                                           ['DD', 'SD', 'CD', 'Final', 'Other'], 0, False)
            if not ok:
                return
            
            session = get_session()
            try:
                # Check if this should be the first active set
                existing_active = session.query(DrawingSet).filter(
                    DrawingSet.project_id == self.project_id,
                    DrawingSet.is_active == True
                ).first()
                
                new_set = DrawingSet(
                    project_id=self.project_id,
                    name=name.strip(),
                    phase_type=phase,
                    is_active=existing_active is None  # Active if no other active sets
                )
                
                session.add(new_set)
                session.commit()
                
                QMessageBox.information(self, "Success", f"Drawing set '{name}' created successfully.")
                self.refresh_data()
                
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to create drawing set:\n{str(e)}")
            finally:
                session.close()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create drawing set:\n{str(e)}")
    
    def edit_selected_set(self):
        """Edit the selected drawing set"""
        selected_rows = self.sets_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Edit Set", "Please select a drawing set to edit.")
            return
        
        row = selected_rows[0].row()
        set_id = self.sets_table.item(row, 0).data(Qt.UserRole)
        
        # Find the drawing set
        drawing_set = next((ds for ds in self.drawing_sets if ds.id == set_id), None)
        if not drawing_set:
            QMessageBox.warning(self, "Edit Set", "Selected drawing set not found.")
            return
        
        # Create edit dialog (simplified)
        from PySide6.QtWidgets import QInputDialog
        
        new_name, ok = QInputDialog.getText(self, "Edit Drawing Set", "Set name:", text=drawing_set.name)
        if not ok or not new_name.strip():
            return
        
        try:
            session = get_session()
            try:
                set_to_edit = session.query(DrawingSet).filter(DrawingSet.id == set_id).first()
                if set_to_edit:
                    set_to_edit.name = new_name.strip()
                    session.commit()
                    QMessageBox.information(self, "Success", "Drawing set updated successfully.")
                    self.refresh_data()
                
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to update drawing set:\n{str(e)}")
            finally:
                session.close()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update drawing set:\n{str(e)}")
    
    def delete_selected_set(self):
        """Delete the selected drawing set"""
        selected_rows = self.sets_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Delete Set", "Please select a drawing set to delete.")
            return
        
        row = selected_rows[0].row()
        set_id = self.sets_table.item(row, 0).data(Qt.UserRole)
        
        # Find the drawing set
        drawing_set = next((ds for ds in self.drawing_sets if ds.id == set_id), None)
        if not drawing_set:
            QMessageBox.warning(self, "Delete Set", "Selected drawing set not found.")
            return
        
        # Confirm deletion
        drawing_count = len(drawing_set.drawings) if drawing_set.drawings else 0
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Delete drawing set '{drawing_set.name}'?\n\n"
            f"This will unassign {drawing_count} drawing(s) from this set.\n"
            f"The drawings themselves will not be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            session = get_session()
            try:
                # Unassign drawings from this set
                session.query(Drawing).filter(Drawing.drawing_set_id == set_id).update({Drawing.drawing_set_id: None})
                
                # Delete the set
                session.query(DrawingSet).filter(DrawingSet.id == set_id).delete()
                
                session.commit()
                QMessageBox.information(self, "Success", "Drawing set deleted successfully.")
                self.refresh_data()
                
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to delete drawing set:\n{str(e)}")
            finally:
                session.close()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete drawing set:\n{str(e)}")
    
    def set_selected_active(self):
        """Set the selected drawing set as active"""
        selected_rows = self.sets_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Set Active", "Please select a drawing set to make active.")
            return
        
        row = selected_rows[0].row()
        set_id = self.sets_table.item(row, 0).data(Qt.UserRole)
        
        try:
            session = get_session()
            try:
                # Deactivate all sets
                session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).update({DrawingSet.is_active: False})
                
                # Activate selected set
                session.query(DrawingSet).filter(DrawingSet.id == set_id).update({DrawingSet.is_active: True})
                
                session.commit()
                QMessageBox.information(self, "Success", "Active drawing set updated.")
                self.refresh_data()
                
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to set active drawing set:\n{str(e)}")
            finally:
                session.close()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set active drawing set:\n{str(e)}")
    
    def accept(self):
        """Handle dialog acceptance"""
        if self.mode == 'create':
            self.create_drawing_set()
        
        super().accept()
    
    def create_drawing_set(self):
        """Create the new drawing set from the creation form"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a name for the drawing set.")
            return
        
        phase = self.phase_combo.currentText()
        description = self.description_edit.toPlainText().strip()
        is_active = self.active_checkbox.isChecked()
        
        try:
            session = get_session()
            try:
                # If setting as active, deactivate others
                if is_active:
                    session.query(DrawingSet).filter(DrawingSet.project_id == self.project_id).update({DrawingSet.is_active: False})
                
                new_set = DrawingSet(
                    project_id=self.project_id,
                    name=name,
                    phase_type=phase,
                    description=description,
                    is_active=is_active
                )
                
                session.add(new_set)
                session.commit()
                
            except Exception as e:
                session.rollback()
                raise
            finally:
                session.close()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create drawing set:\n{str(e)}")
```

### 4.2 Comparison Selection Dialog (`src/ui/dialogs/comparison_selection_dialog.py`)

```python
"""
Dialog for selecting two drawing sets for comparison
"""

from typing import List, Tuple, Optional
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QComboBox, QGroupBox, QTextEdit, QMessageBox)
from PySide6.QtCore import Qt

from models import DrawingSet


class ComparisonSelectionDialog(QDialog):
    """Dialog for selecting base and compare drawing sets"""
    
    def __init__(self, parent, drawing_sets: List[DrawingSet]):
        super().__init__(parent)
        self.drawing_sets = drawing_sets
        self.base_set_id = None
        self.compare_set_id = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Select Drawing Sets for Comparison")
        self.setGeometry(300, 300, 500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Select two drawing sets to compare. Changes will be detected between "
            "the base set (reference) and compare set (new design)."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Selection group
        selection_group = QGroupBox("Drawing Set Selection")
        selection_layout = QVBoxLayout()
        
        # Base set selection
        base_layout = QHBoxLayout()
        base_layout.addWidget(QLabel("Base Set (Reference):"))
        self.base_combo = QComboBox()
        self.populate_combo(self.base_combo)
        self.base_combo.currentTextChanged.connect(self.on_selection_changed)
        base_layout.addWidget(self.base_combo)
        selection_layout.addLayout(base_layout)
        
        # Compare set selection
        compare_layout = QHBoxLayout()
        compare_layout.addWidget(QLabel("Compare Set (New):"))
        self.compare_combo = QComboBox()
        self.populate_combo(self.compare_combo)
        self.compare_combo.currentTextChanged.connect(self.on_selection_changed)
        compare_layout.addWidget(self.compare_combo)
        selection_layout.addLayout(compare_layout)
        
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        # Preview information
        preview_group = QGroupBox("Comparison Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(150)
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        self.compare_button = QPushButton("Start Comparison")
        self.compare_button.clicked.connect(self.accept)
        self.compare_button.setDefault(True)
        self.compare_button.setEnabled(False)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.compare_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Initialize preview
        self.update_preview()
    
    def populate_combo(self, combo: QComboBox):
        """Populate combo box with drawing sets"""
        combo.clear()
        combo.addItem("-- Select Drawing Set --", None)
        
        for drawing_set in self.drawing_sets:
            drawing_count = len(drawing_set.drawings) if drawing_set.drawings else 0
            active_indicator = " (Active)" if drawing_set.is_active else ""
            
            item_text = f"{drawing_set.name} ({drawing_set.phase_type}) - {drawing_count} drawings{active_indicator}"
            combo.addItem(item_text, drawing_set.id)
    
    def on_selection_changed(self):
        """Handle selection changes"""
        self.base_set_id = self.base_combo.currentData()
        self.compare_set_id = self.compare_combo.currentData()
        
        # Enable compare button if both sets selected and different
        can_compare = (
            self.base_set_id is not None and 
            self.compare_set_id is not None and 
            self.base_set_id != self.compare_set_id
        )
        self.compare_button.setEnabled(can_compare)
        
        self.update_preview()
    
    def update_preview(self):
        """Update the comparison preview text"""
        if not self.base_set_id or not self.compare_set_id:
            self.preview_text.setText("Select both drawing sets to see comparison preview.")
            return
        
        if self.base_set_id == self.compare_set_id:
            self.preview_text.setText("⚠️ Please select different drawing sets for comparison.")
            return
        
        # Get set information
        base_set = next((ds for ds in self.drawing_sets if ds.id == self.base_set_id), None)
        compare_set = next((ds for ds in self.drawing_sets if ds.id == self.compare_set_id), None)
        
        if not base_set or not compare_set:
            self.preview_text.setText("Error: Could not find selected drawing sets.")
            return
        
        # Build preview text
        preview_text = f"📊 Comparison Preview:\n\n"
        
        preview_text += f"Base Set: {base_set.name} ({base_set.phase_type})\n"
        preview_text += f"  • {len(base_set.drawings) if base_set.drawings else 0} drawings\n"
        preview_text += f"  • Created: {base_set.created_date.strftime('%Y-%m-%d')}\n\n"
        
        preview_text += f"Compare Set: {compare_set.name} ({compare_set.phase_type})\n"
        preview_text += f"  • {len(compare_set.drawings) if compare_set.drawings else 0} drawings\n"
        preview_text += f"  • Created: {compare_set.created_date.strftime('%Y-%m-%d')}\n\n"
        
        preview_text += "The comparison will analyze:\n"
        preview_text += "  • Room layout changes (added, removed, modified spaces)\n"
        preview_text += "  • HVAC component changes (equipment relocation, additions)\n"
        preview_text += "  • HVAC path routing changes\n"
        preview_text += "  • Acoustic impact analysis\n\n"
        
        # Time estimate
        total_drawings = (len(base_set.drawings) if base_set.drawings else 0) + (len(compare_set.drawings) if compare_set.drawings else 0)
        if total_drawings > 10:
            preview_text += "⏱️ Large drawing sets - comparison may take a few minutes."
        else:
            preview_text += "⏱️ Estimated comparison time: 30-60 seconds."
        
        self.preview_text.setText(preview_text)
    
    def get_selected_sets(self) -> Tuple[int, int]:
        """Get the selected drawing set IDs"""
        return self.base_set_id, self.compare_set_id
    
    def accept(self):
        """Validate and accept the dialog"""
        if not self.base_set_id or not self.compare_set_id:
            QMessageBox.warning(self, "Selection Required", "Please select both base and compare drawing sets.")
            return
        
        if self.base_set_id == self.compare_set_id:
            QMessageBox.warning(self, "Different Sets Required", "Please select different drawing sets for comparison.")
            return
        
        super().accept()
```

### 4.3 Drawing Comparison Interface (`src/ui/drawing_comparison_interface.py`)

```python
"""
Drawing Comparison Interface - Side-by-side drawing comparison with change detection
"""

import json
from typing import List, Optional, Dict
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QSplitter, QLabel, QPushButton, QToolBar, QStatusBar,
                               QGroupBox, QListWidget, QListWidgetItem, QTabWidget,
                               QProgressBar, QMessageBox, QComboBox, QCheckBox,
                               QScrollArea, QFrame)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QPen

from models import get_session, DrawingSet, DrawingComparison, ChangeItem, Drawing
from drawing import PDFViewer, DrawingOverlay
from drawing.drawing_comparison import DrawingComparisonEngine
from ui.dialogs.comparison_results_dialog import ComparisonResultsDialog


class ComparisonWorker(QThread):
    """Background worker for performing drawing comparison"""
    
    progress_updated = Signal(int, str)  # percentage, status message
    comparison_completed = Signal(object)  # DrawingComparison object
    error_occurred = Signal(str)  # error message
    
    def __init__(self, base_set_id: int, compare_set_id: int):
        super().__init__()
        self.base_set_id = base_set_id
        self.compare_set_id = compare_set_id
        self.comparison_engine = DrawingComparisonEngine()
    
    def run(self):
        """Run the comparison in background"""
        try:
            self.progress_updated.emit(10, "Initializing comparison...")
            
            self.progress_updated.emit(30, "Analyzing spaces...")
            
            self.progress_updated.emit(60, "Detecting HVAC changes...")
            
            self.progress_updated.emit(80, "Calculating acoustic impact...")
            
            # Perform actual comparison
            comparison = self.comparison_engine.compare_drawing_sets(self.base_set_id, self.compare_set_id)
            
            self.progress_updated.emit(100, "Comparison complete!")
            self.comparison_completed.emit(comparison)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class DrawingComparisonInterface(QMainWindow):
    """Main interface for side-by-side drawing comparison"""
    
    def __init__(self, base_set_id: int, compare_set_id: int):
        super().__init__()
        self.base_set_id = base_set_id
        self.compare_set_id = compare_set_id
        self.comparison = None
        self.change_items = []
        
        # Viewer synchronization
        self.sync_enabled = True
        self.sync_zoom = True
        self.sync_pan = True
        
        # Load drawing sets
        self.load_drawing_sets()
        
        # Initialize UI
        self.init_ui()
        
        # Start comparison
        QTimer.singleShot(1000, self.start_comparison)
    
    def load_drawing_sets(self):
        """Load drawing set information"""
        session = get_session()
        try:
            self.base_set = session.query(DrawingSet).filter(DrawingSet.id == self.base_set_id).first()
            self.compare_set = session.query(DrawingSet).filter(DrawingSet.id == self.compare_set_id).first()
            
            if not self.base_set or not self.compare_set:
                raise Exception("Could not load drawing sets")
                
        finally:
            session.close()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"Drawing Comparison: {self.base_set.name} vs {self.compare_set.name}")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Header with set information
        self.create_header(main_layout)
        
        # Main comparison area
        comparison_splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Base set viewer
        base_widget = self.create_viewer_widget("Base", self.base_set)
        comparison_splitter.addWidget(base_widget)
        
        # Right side: Compare set viewer  
        compare_widget = self.create_viewer_widget("Compare", self.compare_set)
        comparison_splitter.addWidget(compare_widget)
        
        # Bottom panel: Changes and controls
        bottom_splitter = QSplitter(Qt.Vertical)
        bottom_splitter.addWidget(comparison_splitter)
        
        changes_widget = self.create_changes_widget()
        bottom_splitter.addWidget(changes_widget)
        
        # Set splitter proportions
        bottom_splitter.setSizes([700, 300])
        
        main_layout.addWidget(bottom_splitter)
        central_widget.setLayout(main_layout)
        
        # Create status bar
        self.create_status_bar()
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction('Export Comparison Report', self.export_comparison_report)
        file_menu.addSeparator()
        file_menu.addAction('Close', self.close)
        
        # View menu
        view_menu = menubar.addMenu('View')
        view_menu.addAction('Sync Viewers', self.toggle_sync)
        view_menu.addAction('Show All Changes', self.show_all_changes)
        view_menu.addAction('Hide Changes', self.hide_changes)
        
        # Analysis menu
        analysis_menu = menubar.addMenu('Analysis')
        analysis_menu.addAction('Detailed Results', self.show_detailed_results)
        analysis_menu.addAction('Acoustic Impact Report', self.show_acoustic_impact)
    
    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Sync controls
        toolbar.addWidget(QLabel("Synchronization:"))
        
        self.sync_checkbox = QCheckBox("Sync Viewers")
        self.sync_checkbox.setChecked(True)
        self.sync_checkbox.toggled.connect(self.set_sync_enabled)
        toolbar.addWidget(self.sync_checkbox)
        
        toolbar.addSeparator()
        
        # Change filters
        toolbar.addWidget(QLabel("Show Changes:"))
        
        self.changes_combo = QComboBox()
        self.changes_combo.addItems(['All Changes', 'Critical Only', 'High Priority', 'Spaces Only', 'HVAC Only'])
        self.changes_combo.currentTextChanged.connect(self.filter_changes)
        toolbar.addWidget(self.changes_combo)
        
        toolbar.addSeparator()
        
        # Action buttons
        self.results_button = QPushButton("Detailed Results")
        self.results_button.clicked.connect(self.show_detailed_results)
        self.results_button.setEnabled(False)
        toolbar.addWidget(self.results_button)
    
    def create_header(self, layout):
        """Create header with drawing set information"""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        
        # Base set info
        base_group = QGroupBox(f"Base: {self.base_set.name}")
        base_layout = QVBoxLayout()
        base_layout.addWidget(QLabel(f"Phase: {self.base_set.phase_type}"))
        base_layout.addWidget(QLabel(f"Drawings: {len(self.base_set.drawings) if self.base_set.drawings else 0}"))
        base_layout.addWidget(QLabel(f"Created: {self.base_set.created_date.strftime('%Y-%m-%d')}"))
        base_group.setLayout(base_layout)
        header_layout.addWidget(base_group)
        
        # Comparison status
        status_group = QGroupBox("Comparison Status")
        status_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to compare...")
        
        status_layout.addWidget(self.progress_label)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        header_layout.addWidget(status_group)
        
        # Compare set info
        compare_group = QGroupBox(f"Compare: {self.compare_set.name}")
        compare_layout = QVBoxLayout()
        compare_layout.addWidget(QLabel(f"Phase: {self.compare_set.phase_type}"))
        compare_layout.addWidget(QLabel(f"Drawings: {len(self.compare_set.drawings) if self.compare_set.drawings else 0}"))
        compare_layout.addWidget(QLabel(f"Created: {self.compare_set.created_date.strftime('%Y-%m-%d')}"))
        compare_group.setLayout(compare_layout)
        header_layout.addWidget(compare_group)
        
        header_widget.setLayout(header_layout)
        layout.addWidget(header_widget)
    
    def create_viewer_widget(self, title: str, drawing_set: DrawingSet):
        """Create a viewer widget for a drawing set"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(f"{title}: {drawing_set.name} ({drawing_set.phase_type})")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # PDF viewer placeholder (would integrate with actual PDFViewer)
        viewer_frame = QFrame()
        viewer_frame.setFrameStyle(QFrame.Box)
        viewer_frame.setMinimumSize(600, 400)
        
        viewer_layout = QVBoxLayout()
        viewer_placeholder = QLabel("PDF Viewer\n(Integration with PDFViewer component)")
        viewer_placeholder.setAlignment(Qt.AlignCenter)
        viewer_placeholder.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        viewer_layout.addWidget(viewer_placeholder)
        viewer_frame.setLayout(viewer_layout)
        
        layout.addWidget(viewer_frame)
        
        # Drawing selection
        drawing_layout = QHBoxLayout()
        drawing_layout.addWidget(QLabel("Drawing:"))
        
        drawing_combo = QComboBox()
        if drawing_set.drawings:
            for drawing in drawing_set.drawings:
                drawing_combo.addItem(drawing.name, drawing.id)
        
        drawing_layout.addWidget(drawing_combo)
        layout.addLayout(drawing_layout)
        
        widget.setLayout(layout)
        return widget
    
    def create_changes_widget(self):
        """Create the changes analysis widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Changes header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Detected Changes"))
        
        self.changes_count_label = QLabel("0 changes")
        header_layout.addWidget(self.changes_count_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Changes tabs
        tabs = QTabWidget()
        
        # All changes tab
        self.changes_list = QListWidget()
        tabs.addTab(self.changes_list, "All Changes")
        
        # Critical changes tab
        self.critical_list = QListWidget()
        tabs.addTab(self.critical_list, "Critical")
        
        # Summary tab
        self.summary_widget = QWidget()
        summary_layout = QVBoxLayout()
        self.summary_text = QLabel("Comparison not started")
        summary_layout.addWidget(self.summary_text)
        self.summary_widget.setLayout(summary_layout)
        tabs.addTab(self.summary_widget, "Summary")
        
        layout.addWidget(tabs)
        widget.setLayout(layout)
        
        return widget
    
    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def start_comparison(self):
        """Start the drawing comparison process"""
        self.progress_label.setText("Starting comparison...")
        self.progress_bar.setValue(0)
        
        # Create and start worker thread
        self.comparison_worker = ComparisonWorker(self.base_set_id, self.compare_set_id)
        self.comparison_worker.progress_updated.connect(self.update_progress)
        self.comparison_worker.comparison_completed.connect(self.on_comparison_completed)
        self.comparison_worker.error_occurred.connect(self.on_comparison_error)
        
        self.comparison_worker.start()
    
    def update_progress(self, percentage: int, message: str):
        """Update progress bar and message"""
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(message)
        self.status_bar.showMessage(message)
    
    def on_comparison_completed(self, comparison: DrawingComparison):
        """Handle completed comparison"""
        self.comparison = comparison
        
        # Load change items
        session = get_session()
        try:
            self.change_items = session.query(ChangeItem).filter(ChangeItem.comparison_id == comparison.id).all()
        finally:
            session.close()
        
        # Update UI
        self.update_changes_display()
        self.progress_label.setText(f"Comparison complete - {comparison.total_changes} changes detected")
        self.results_button.setEnabled(True)
        
        # Show summary
        self.show_comparison_summary()
    
    def on_comparison_error(self, error_message: str):
        """Handle comparison error"""
        self.progress_label.setText("Comparison failed")
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Comparison Error", f"Failed to compare drawing sets:\n{error_message}")
    
    def update_changes_display(self):
        """Update the changes display with detected changes"""
        if not self.change_items:
            return
        
        # Clear lists
        self.changes_list.clear()
        self.critical_list.clear()
        
        # Sort changes by severity
        sorted_changes = sorted(self.change_items, key=lambda x: {
            'critical': 0, 'high': 1, 'medium': 2, 'low': 3
        }.get(x.severity, 4))
        
        critical_count = 0
        
        for change in sorted_changes:
            # Create display text
            change_details = json.loads(change.change_details) if change.change_details else {}
            element_name = change_details.get('name', f"{change.element_type}_{change.id}")
            
            # Icons for change types
            change_icons = {
                'added': '➕',
                'removed': '➖', 
                'modified': '📝',
                'moved': '↔️'
            }
            
            # Severity colors
            severity_colors = {
                'critical': QColor(255, 99, 99),   # Red
                'high': QColor(255, 165, 0),       # Orange
                'medium': QColor(255, 215, 0),     # Yellow
                'low': QColor(144, 238, 144)       # Green
            }
            
            icon = change_icons.get(change.change_type, '❓')
            item_text = f"{icon} {element_name} - {change.change_type} ({change.severity})"
            
            # Add to all changes list
            all_item = QListWidgetItem(item_text)
            all_item.setData(Qt.UserRole, change.id)
            if change.severity in severity_colors:
                all_item.setForeground(severity_colors[change.severity])
            self.changes_list.addItem(all_item)
            
            # Add to critical list if critical
            if change.severity == 'critical':
                critical_count += 1
                critical_item = QListWidgetItem(item_text)
                critical_item.setData(Qt.UserRole, change.id)
                critical_item.setForeground(severity_colors['critical'])
                self.critical_list.addItem(critical_item)
        
        # Update count label
        self.changes_count_label.setText(f"{len(self.change_items)} changes ({critical_count} critical)")
    
    def show_comparison_summary(self):
        """Show comparison summary in the summary tab"""
        if not self.comparison:
            return
        
        try:
            results = json.loads(self.comparison.comparison_results) if self.comparison.comparison_results else {}
            summary = results.get('summary', {})
            
            summary_text = f"Comparison Summary:\n\n"
            summary_text += f"Total Changes: {summary.get('total_changes', 0)}\n"
            summary_text += f"  • Space Changes: {summary.get('space_changes', 0)}\n"
            summary_text += f"  • HVAC Changes: {summary.get('hvac_changes', 0)}\n"
            summary_text += f"  • Path Changes: {summary.get('path_changes', 0)}\n\n"
            summary_text += f"Critical Changes: {summary.get('critical_changes', 0)}\n"
            summary_text += f"Acoustic Impact Score: {self.comparison.acoustic_impact_score:.1f}/100\n\n"
            summary_text += f"Comparison Date: {self.comparison.comparison_date.strftime('%Y-%m-%d %H:%M')}"
            
            self.summary_text.setText(summary_text)
            
        except Exception as e:
            self.summary_text.setText(f"Error loading summary: {str(e)}")
    
    def show_detailed_results(self):
        """Show detailed comparison results dialog"""
        if not self.comparison:
            QMessageBox.information(self, "No Results", "No comparison results available.")
            return
        
        try:
            dialog = ComparisonResultsDialog(self, self.comparison)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show detailed results:\n{str(e)}")
    
    def show_acoustic_impact(self):
        """Show acoustic impact analysis"""
        QMessageBox.information(self, "Acoustic Impact", "Acoustic impact analysis feature coming soon.")
    
    def export_comparison_report(self):
        """Export comparison report to Excel"""
        if not self.comparison:
            QMessageBox.information(self, "No Results", "No comparison results to export.")
            return
        
        QMessageBox.information(self, "Export Report", "Export functionality will be implemented.")
    
    def toggle_sync(self):
        """Toggle viewer synchronization"""
        self.sync_enabled = not self.sync_enabled
        self.sync_checkbox.setChecked(self.sync_enabled)
    
    def set_sync_enabled(self, enabled: bool):
        """Set viewer synchronization enabled/disabled"""
        self.sync_enabled = enabled
    
    def show_all_changes(self):
        """Show all changes in viewers"""
        self.changes_combo.setCurrentText("All Changes")
        self.filter_changes("All Changes")
    
    def hide_changes(self):
        """Hide change overlays in viewers"""
        pass  # Would hide overlays in PDF viewers
    
    def filter_changes(self, filter_type: str):
        """Filter displayed changes based on type"""
        # Would filter the change overlays in the PDF viewers
        pass
```

## Phase 5: Implementation Steps and Testing

### 5.1 Implementation Order

1. **Database Models** (Phase 1)
   - Create new models and migration script
   - Test database creation and migration on fresh and existing databases

2. **Core Comparison Engine** (Phase 2) 
   - Implement drawing comparison algorithms
   - Test with sample data sets

3. **Project Dashboard Enhancement** (Phase 3)
   - Add drawing sets tab and enhanced drawings display
   - Test set management workflows

4. **UI Components** (Phase 4)
   - Build dialogs and comparison interface
   - Integrate with existing PDF viewer system

5. **Testing and Refinement**
   - End-to-end testing with real project data
   - Performance optimization for large drawing sets
   - User experience refinement

### 5.2 Testing Strategy

- **Unit Tests**: Test individual comparison algorithms
- **Integration Tests**: Test database operations and UI workflows  
- **User Acceptance Tests**: Test complete comparison workflows
- **Performance Tests**: Test with large drawing sets and complex projects

This comprehensive implementation plan provides a complete drawing sets comparison system while maintaining compatibility with the existing SQLite database structure and following established patterns in the codebase.