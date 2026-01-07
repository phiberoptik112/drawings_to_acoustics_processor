# Match Line Coordinate System - Future Feature Planning

## Overview

This document outlines the planned feature for enabling HVAC paths and spaces to span multiple drawings by establishing a building-wide coordinate system using match line reference points.

## Problem Statement

Currently, HVAC paths are tied to specific drawings. However, in real construction projects:
- Mechanical drawings often cover different areas of a building
- A single duct path may span multiple drawings
- Users need to correlate locations between architectural and mechanical drawings
- Match lines on drawings indicate where sheets overlap or connect

## Proposed Solution

### User Workflow

1. User enters "Match Line Mode" via toolbar button
2. User clicks on a drawing to place a reference point at a match line intersection
3. Dialog prompts for building coordinates (grid reference like "A-1" or absolute coordinates)
4. User repeats on other drawings to establish the same reference point
5. System calculates transformation matrices between drawings
6. Paths can then be displayed across drawings using building coordinates

### Database Models

#### BuildingGrid
```python
class BuildingGrid(Base):
    """Building-wide coordinate reference system"""
    __tablename__ = 'building_grids'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    name = Column(String(255), default='Primary Grid')
    
    # Origin point in building coordinates
    origin_x = Column(Float, default=0.0)
    origin_y = Column(Float, default=0.0)
    
    # Grid rotation from true north (degrees)
    rotation_angle = Column(Float, default=0.0)
    
    # Scale: feet per unit
    unit_scale = Column(Float, default=1.0)
    
    # Grid labeling
    x_axis_prefix = Column(String(10), default='')  # e.g., 'A', 'B', 'C' or '1', '2', '3'
    y_axis_prefix = Column(String(10), default='')
    
    created_date = Column(DateTime, default=datetime.utcnow)
```

#### MatchLinePoint
```python
class MatchLinePoint(Base):
    """A reference point on a specific drawing that maps to building coordinates"""
    __tablename__ = 'match_line_points'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    building_grid_id = Column(Integer, ForeignKey('building_grids.id'))
    
    # Which drawing this point is on
    drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=False)
    page_number = Column(Integer, default=1)
    
    # Position in drawing pixels
    drawing_x = Column(Float, nullable=False)
    drawing_y = Column(Float, nullable=False)
    
    # Position in building coordinates
    building_x = Column(Float, nullable=False)
    building_y = Column(Float, nullable=False)
    
    # Human-readable label
    label = Column(String(100))  # e.g., "Grid A-1", "Match Line ML-3", "Column C4"
    
    # Point classification
    point_type = Column(String(50))  # 'grid_intersection', 'match_line', 'column', 'custom'
    
    created_date = Column(DateTime, default=datetime.utcnow)
```

#### DrawingAlignment
```python
class DrawingAlignment(Base):
    """Stores computed transformation for a drawing"""
    __tablename__ = 'drawing_alignments'
    
    id = Column(Integer, primary_key=True)
    drawing_id = Column(Integer, ForeignKey('drawings.id'), nullable=False)
    page_number = Column(Integer, default=1)
    building_grid_id = Column(Integer, ForeignKey('building_grids.id'))
    
    # Transformation parameters (2D affine)
    scale_factor = Column(Float)  # Drawing scale relative to building
    rotation = Column(Float)       # Rotation offset (radians)
    offset_x = Column(Float)       # Translation X
    offset_y = Column(Float)       # Translation Y
    
    # Quality metrics
    is_calibrated = Column(Boolean, default=False)  # True if 2+ match points defined
    calibration_error = Column(Float)  # RMS error of calibration (pixels)
    num_reference_points = Column(Integer, default=0)
    
    last_calibrated = Column(DateTime)
```

### UI Components

#### Match Line Tool
- New toolbar button with grid/crosshair icon
- When active, clicks on drawing place reference points
- Visual markers show placed points with labels
- Right-click menu to edit/delete points

#### Calibration Dialog
- Shows list of match points on current drawing
- Input fields for building coordinates
- Option to link to existing point on another drawing
- "Auto-detect" button to find grid intersections in PDF (future)

#### Alignment Status Indicator
- Status bar indicator showing calibration state
- Icon: ✓ Green (calibrated), ⚠ Yellow (partial), ✗ Red (not calibrated)
- Tooltip shows number of reference points and error

### Coordinate Transformation Module

New file: `src/calculations/coordinate_transform.py`

```python
class CoordinateTransformer:
    """Handles coordinate transformation between drawings and building coordinates"""
    
    def __init__(self, project_id):
        self.project_id = project_id
        self._alignment_cache = {}
    
    def transform_to_building(self, drawing_id, page_number, x, y):
        """Convert drawing coordinates to building coordinates"""
        alignment = self._get_alignment(drawing_id, page_number)
        if not alignment or not alignment.is_calibrated:
            return None, None
        
        # Apply inverse affine transformation
        # ... matrix math ...
        return building_x, building_y
    
    def transform_from_building(self, drawing_id, page_number, building_x, building_y):
        """Convert building coordinates to drawing coordinates"""
        alignment = self._get_alignment(drawing_id, page_number)
        if not alignment or not alignment.is_calibrated:
            return None, None
        
        # Apply forward affine transformation
        # ... matrix math ...
        return drawing_x, drawing_y
    
    def calculate_alignment(self, drawing_id, page_number):
        """Compute alignment from match points using least squares fit"""
        # Load match points for this drawing
        # Compute affine transformation matrix
        # Store in DrawingAlignment table
        pass
    
    def get_path_building_bounds(self, hvac_path_id):
        """Get the bounding box of a path in building coordinates"""
        pass
    
    def find_drawings_containing_region(self, building_x1, building_y1, building_x2, building_y2):
        """Find all drawings that overlap a building coordinate region"""
        pass
```

### Path Spanning Logic

When displaying a path:
1. Load path's HVACComponents with their drawing coordinates
2. Check if current drawing is calibrated
3. If YES:
   - Transform all component positions to building coordinates
   - Transform building coordinates to current drawing coordinates
   - Display components/segments that fall within drawing bounds
4. If NO:
   - Only show components that were directly placed on this drawing

### Visual Indicators

- Paths that span multiple drawings show a special indicator
- "Partial path" warning when viewing only part of a path
- Option to "Show full path" opens multi-drawing view

## Implementation Phases

### Phase 1: Foundation
- Create database models
- Add migration
- Implement basic coordinate transformation math

### Phase 2: UI - Point Placement
- Add match line tool to toolbar
- Implement click-to-place functionality
- Create basic calibration dialog

### Phase 3: Alignment Calculation
- Implement least-squares fitting for alignment
- Add calibration error calculation
- Status indicators

### Phase 4: Cross-Drawing Display
- Update path rendering to use building coordinates
- Handle partial path display
- Add multi-drawing path view

## Future Enhancements

- Auto-detect grid lines in PDF using image processing
- Import grid coordinates from CAD/BIM files
- 3D building model integration
- Print/export with match line annotations

## Dependencies

- NumPy for matrix operations (already in project)
- Optional: OpenCV for grid detection (future)

## Estimated Effort

- Phase 1: 4-6 hours
- Phase 2: 6-8 hours
- Phase 3: 4-6 hours
- Phase 4: 8-12 hours

Total: ~25-35 hours for full implementation

