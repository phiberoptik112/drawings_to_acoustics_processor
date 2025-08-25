# Drawing Overlay Debug Plan

## Issue Summary

Two critical bugs have been identified in the drawing overlay system:

1. **Double-click Issue**: Once an element's position has been edited by the user, it can't be double-clicked on (gives 'no component found error')
2. **Element List Cleanup**: Once a Path has been made from components and segments, the elements should be cleared from the Element List

## Root Cause Analysis

### Issue 1: Double-Click After Position Edit

**Root Cause**: Coordinate system inconsistency between base cache and current coordinates.

**Technical Details**:
- Components are moved by directly modifying their `x,y` coordinates in `_handle_select_move()` (lines 826-827 in drawing_overlay.py)
- The system maintains two coordinate systems: current coordinates and base coordinates (for zoom handling)
- When `_base_dirty = True` is set after moves, the base cache is rebuilt by dividing current coordinates by current zoom factor
- If the component was moved at one zoom level but base cache is rebuilt at a different zoom level, coordinate inconsistencies occur
- Hit testing only uses current `x,y` coordinates but these may be desynchronized

**Evidence**:
```python
# In _handle_select_move():
comp['x'] = int(comp.get('x', 0)) + dx  # Direct coordinate modification
comp['y'] = int(comp.get('y', 0)) + dy
self._base_dirty = True  # Marks for base cache rebuild

# In _hit_test_component():
comp_x = comp.get('x', 0)  # Uses current coordinates only
comp_y = comp.get('y', 0)
if abs(point.x() - comp_x) <= 16 and abs(point.y() - comp_y) <= 16:
    return comp
```

### Issue 2: Element List Not Cleared After Path Creation

**Root Cause**: Missing cleanup logic after successful HVAC path creation.

**Technical Details**:
- In `create_hvac_path_from_components()` (drawing_interface.py:1223), after successful path creation:
  - Path elements are registered in overlay for show/hide functionality
  - Success message is shown
  - Paths list is refreshed
  - **BUT**: Components and segments are NOT removed from the drawing overlay or elements list
- The elements remain visible and selectable, causing confusion about whether they're still "available" for new paths

## Proposed Solutions

### Fix 1: Coordinate System Synchronization

**Approach 1 - Immediate Base Cache Update (Recommended)**:
```python
def _handle_select_move(self, point):
    # ... existing code ...
    if self._hit_target and self._hit_target.get('type') == 'component':
        for comp in (self._selected_components or [self._hit_target.get('ref')]):
            if not isinstance(comp, dict):
                continue
            old_x, old_y = comp.get('x', 0), comp.get('y', 0)
            comp['x'] = int(old_x) + dx
            comp['y'] = int(old_y) + dy
            pos = comp.get('position')
            if isinstance(pos, dict):
                pos['x'] = int(pos.get('x', 0)) + dx
                pos['y'] = int(pos.get('y', 0)) + dy
            self._update_segments_for_component_move(comp)
            
            # IMMEDIATE base cache update for moved component
            self._update_component_base_coordinates(comp)
    
    # Remove the blanket _base_dirty = True and update only affected elements
    self.update()

def _update_component_base_coordinates(self, component):
    """Update base coordinates for a specific component"""
    cur_z = self._current_zoom_factor or 1.0
    # Find and update the component in base cache
    for i, bc in enumerate(self._base_components):
        if bc.get('id') == component.get('id') or \
           (bc.get('component_type') == component.get('component_type') and 
            abs(bc.get('x', 0) * cur_z - component.get('x', 0)) < 5):
            self._base_components[i]['x'] = int(component.get('x', 0) / cur_z)
            self._base_components[i]['y'] = int(component.get('y', 0) / cur_z)
            if isinstance(component.get('position'), dict):
                self._base_components[i]['position'] = {
                    'x': int(component['position'].get('x', 0) / cur_z),
                    'y': int(component['position'].get('y', 0) / cur_z),
                }
            break
```

**Approach 2 - Hit Test Improvement**:
```python
def _hit_test_component(self, point):
    """Improved hit testing that accounts for coordinate inconsistencies"""
    for comp in self.components:
        comp_x = comp.get('x', 0)
        comp_y = comp.get('y', 0)
        
        # Primary hit test
        if abs(point.x() - comp_x) <= 16 and abs(point.y() - comp_y) <= 16:
            return comp
        
        # Fallback: check position dict if available (coordinate redundancy)
        pos = comp.get('position')
        if isinstance(pos, dict):
            pos_x, pos_y = pos.get('x', 0), pos.get('y', 0)
            if abs(point.x() - pos_x) <= 16 and abs(point.y() - pos_y) <= 16:
                return comp
    return None
```

### Fix 2: Element List Cleanup After Path Creation

**Solution**: Add element removal logic after successful path creation.

```python
# In drawing_interface.py create_hvac_path_from_components():
if hvac_path:
    # Register path elements in drawing overlay for show/hide functionality
    if self.drawing_overlay:
        self.drawing_overlay.register_path_elements(hvac_path.id, components, path_segments)
    
    # NEW: Remove used components and segments from drawing overlay
    self.clear_used_elements_from_overlay(components, path_segments)
    
    # Show success message...
    # ... rest of existing code

def clear_used_elements_from_overlay(self, used_components, used_segments):
    """Remove components and segments that were used in path creation from the overlay"""
    try:
        # Remove components
        for comp in used_components:
            if comp in self.drawing_overlay.components:
                self.drawing_overlay.components.remove(comp)
        
        # Remove segments  
        for seg in used_segments:
            if seg in self.drawing_overlay.segments:
                self.drawing_overlay.segments.remove(seg)
        
        # Mark base cache as dirty and update
        self.drawing_overlay._base_dirty = True
        self.drawing_overlay.update()
        
        # Refresh the elements list display
        overlay_data = self.drawing_overlay.get_elements_data()
        self.rebuild_elements_list(overlay_data)
        self.update_elements_display()
        
    except Exception as e:
        print(f"Warning: Failed to clear used elements: {e}")
```

### Alternative Fix 2: User Choice Dialog

```python
def create_hvac_path_from_components(self, components, segments):
    # ... existing path creation code ...
    
    if hvac_path:
        # Register path elements
        if self.drawing_overlay:
            self.drawing_overlay.register_path_elements(hvac_path.id, components, path_segments)
        
        # Ask user if they want to clear used elements
        reply = QMessageBox.question(
            self, 
            "Path Created Successfully", 
            f"HVAC path '{hvac_path.name}' was created successfully.\n\n"
            f"Would you like to remove the used components and segments from the drawing?\n"
            f"(They will still be available as part of the saved path)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.clear_used_elements_from_overlay(components, path_segments)
        
        # ... rest of existing code
```

## Implementation Priority

1. **High Priority**: Fix 1 - Coordinate system synchronization (blocks basic functionality)
2. **Medium Priority**: Fix 2 - Element cleanup (UX improvement, workflow confusion)

## Testing Plan

### Test Case 1: Double-Click After Move
1. Create a component (fan/grille/etc.)
2. Switch to select tool
3. Drag component to new position
4. Try to double-click on moved component
5. Verify dialog opens successfully

### Test Case 2: Element List Cleanup
1. Create 2+ components and 1+ segments connecting them
2. Select components and create HVAC path
3. Verify path creation succeeds
4. Check that elements list no longer shows the used components/segments
5. Verify path shows up in paths list
6. Test path show/hide functionality still works

### Test Case 3: Zoom Consistency
1. Create component at zoom 100%
2. Zoom to 150%
3. Move component
4. Zoom back to 100%
5. Verify double-click still works
6. Verify component renders at correct position

## Risk Assessment

- **Low Risk**: Both fixes are localized to specific functionality areas
- **Base Cache Logic**: Changes to zoom/coordinate handling need thorough testing
- **UI Consistency**: Element removal after path creation should be reversible (undo functionality)

## Additional Considerations

1. **Undo/Redo**: Consider how element removal affects undo functionality
2. **Path Editing**: If paths can be edited, elements might need to be restored
3. **Multiple Path Creation**: Ensure elements can be shared across multiple paths if needed
4. **Performance**: Base cache updates should be efficient for large drawings