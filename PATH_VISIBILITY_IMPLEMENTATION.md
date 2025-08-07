# Path Visibility Implementation Guide

## Overview

This document describes a robust pattern for implementing selective element visibility in Qt-based drawing applications. The technique allows users to show/hide groups of drawing elements (paths) through UI controls, with reliable state management and visual feedback.

## Problem Context

### Initial Challenge
- Drawing overlay contained multiple elements (components and segments)
- Users needed ability to hide/show complete paths containing multiple elements
- Standard checkbox signals in QListWidget had reliability issues
- Elements belonging to incomplete database paths remained visible

### Core Requirements
- Reliable show/hide functionality for grouped drawing elements
- Visual feedback for current visibility state
- Database-driven element grouping
- Fallback mechanisms for UI control failures

## Technical Architecture

### 1. Element-Path Mapping System

```python
# Drawing overlay stores path-to-elements mapping
self.path_element_mapping = {}  # Maps path_id to {components: [], segments: []}

def register_path_elements(self, path_id: int, components: list, segments: list):
    """Register which components and segments belong to a path"""
    self.path_element_mapping[path_id] = {
        'components': components.copy(),
        'segments': segments.copy()
    }
```

**Benefits:**
- Decouples UI controls from element storage
- Allows dynamic registration of elements to paths
- Supports multiple paths with overlapping elements

### 2. Conditional Rendering Pattern

```python
def draw_components(self, painter):
    """Draw HVAC components with visibility filtering"""
    for comp_data in self.components:
        # Check if this component belongs to a hidden path
        if self.is_component_hidden_by_path(comp_data):
            continue
        # ... render component
        
def is_component_hidden_by_path(self, comp_data: dict) -> bool:
    """Check if a component should be hidden because its path is hidden"""
    for path_id, mapping in self.path_element_mapping.items():
        for path_comp in mapping['components']:
            # Match by position and type since components might not have unique IDs
            if (comp_data.get('x') == path_comp.get('x') and 
                comp_data.get('y') == path_comp.get('y') and
                comp_data.get('component_type') == path_comp.get('component_type')):
                # This component belongs to a path, check if path is visible
                return path_id not in self.visible_paths
    return False
```

**Key Principles:**
- **Filter-based rendering**: Elements are filtered during paint rather than removed
- **Position-based matching**: Uses coordinates for element identification when IDs aren't reliable
- **Early exit**: Skip rendering entirely for hidden elements

### 3. Robust UI Control Pattern

#### Problem with Standard Approach
```python
# PROBLEMATIC: QListWidget + setItemWidget + QCheckBox signals unreliable
checkbox = QCheckBox()
checkbox.stateChanged.connect(handler)  # May not fire consistently
```

#### Solution: Multiple Control Mechanisms
```python
# 1. Primary: Toggle Button with Visual Feedback
toggle_btn = QPushButton("👁️‍🗨️")  # Hidden eye initially
toggle_btn.setCheckable(True)
toggle_btn.setStyleSheet("""
    QPushButton:checked {
        background-color: #4CAF50;
        border: 1px solid #45a049;
    }
""")
toggle_btn.clicked.connect(lambda checked, pid=path_id: self.toggle_path_visibility(pid, checked))

# 2. Backup: Direct Handler Calls
def force_show_path(self, path_id: int):
    """Bypass UI controls and directly call visibility handler"""
    self.handle_path_visibility_changed(path_id, True)

# 3. Bulk Operations
def show_all_paths(self):
    """Programmatically activate all toggle buttons"""
    for toggle_btn in self.get_all_toggle_buttons():
        if not toggle_btn.isChecked():
            toggle_btn.setChecked(True)
            toggle_btn.clicked.emit(True)
```

**Reliability Features:**
- **Multiple activation methods**: UI controls + programmatic + fallback
- **Visual state indicators**: Icons and colors show current state
- **Bypass mechanisms**: Direct handler calls when UI fails

### 4. State Management System

```python
# Centralized visibility state
self.visible_paths = {}  # Set of visible path IDs

def handle_path_visibility_changed(self, path_id: int, visible: bool):
    """Central handler for all visibility changes"""
    if visible:
        self.visible_paths[path_id] = True
        self.show_path_on_drawing(path_id)
    else:
        self.visible_paths.pop(path_id, None)
        self.hide_path_on_drawing(path_id)
    
    # Trigger repaint
    if self.drawing_overlay:
        self.drawing_overlay.update()
```

**State Principles:**
- **Single source of truth**: `visible_paths` dictionary holds authoritative state
- **Immediate updates**: State changes trigger immediate overlay repaints
- **Consistent API**: All visibility changes go through central handler

## Implementation Steps

### Step 1: Add Element Mapping Storage
```python
# In your drawing overlay class
self.path_element_mapping = {}
self.visible_paths = {}
```

### Step 2: Implement Registration System
```python
def register_path_elements(self, path_id: int, components: list, segments: list):
    self.path_element_mapping[path_id] = {
        'components': components.copy(),
        'segments': segments.copy()
    }
```

### Step 3: Add Visibility Filtering to Render Methods
```python
def draw_components(self, painter):
    for comp_data in self.components:
        if self.is_component_hidden_by_path(comp_data):
            continue
        # ... existing render code
```

### Step 4: Create Reliable UI Controls
```python
# Replace unreliable checkboxes with toggle buttons
toggle_btn = QPushButton("👁️‍🗨️")
toggle_btn.setCheckable(True)
toggle_btn.clicked.connect(self.toggle_path_visibility)
```

### Step 5: Implement Registration Trigger
```python
# Provide way for users to register all current elements to paths
def register_all_elements_to_path(self, path_id: int):
    overlay_data = self.drawing_overlay.get_elements_data()
    all_components = overlay_data.get('components', [])
    all_segments = overlay_data.get('segments', [])
    self.drawing_overlay.register_path_elements(path_id, all_components, all_segments)
```

## Key Design Patterns

### 1. **Separation of Concerns**
- **UI Layer**: Handles user interactions and visual feedback
- **State Layer**: Manages visibility state and business logic
- **Rendering Layer**: Applies visibility filters during paint

### 2. **Multiple Activation Paths**
- **Primary UI**: Toggle buttons for normal user interaction
- **Programmatic**: Batch operations like show/hide all
- **Fallback**: Direct handler calls for debugging/recovery

### 3. **Position-Based Element Matching**
```python
# Robust matching when IDs aren't available
def elements_match(elem1, elem2):
    return (elem1.get('x') == elem2.get('x') and 
            elem1.get('y') == elem2.get('y') and
            elem1.get('type') == elem2.get('type'))
```

### 4. **Immediate Visual Feedback**
```python
# Update UI state immediately when visibility changes
if visible:
    button.setText("👁️")  # Open eye
    button.setStyleSheet("background-color: #4CAF50")
else:
    button.setText("👁️‍🗨️")  # Closed eye  
    button.setStyleSheet("")
```

## Testing Strategy

### 1. **Component-Level Testing**
```python
# Test element registration
assert len(overlay.path_element_mapping[path_id]['components']) == expected_count

# Test visibility filtering
assert overlay.is_component_hidden_by_path(component) == expected_hidden_state
```

### 2. **Integration Testing**
```python
# Test full show/hide cycle
register_path_elements(path_id, components, segments)
toggle_path_visibility(path_id, False)  # Hide
assert all_elements_hidden()
toggle_path_visibility(path_id, True)   # Show  
assert all_elements_visible()
```

### 3. **UI Testing**
```python
# Test multiple activation methods
button.click()  # Primary UI
force_show_path(path_id)  # Fallback
show_all_paths()  # Bulk operation
```

## Common Pitfalls and Solutions

### 1. **QListWidget Checkbox Signal Issues**
**Problem**: `stateChanged` signals don't fire reliably in `QListWidget` with `setItemWidget`
**Solution**: Use `QPushButton` with `setCheckable(True)` instead

### 2. **Element ID Reliability**
**Problem**: Database elements may not have stable IDs for matching
**Solution**: Use position + type-based matching as fallback

### 3. **Partial Path Registration** 
**Problem**: Database paths may be incomplete (missing some visual elements)
**Solution**: Provide "register all elements" function to capture complete visual state

### 4. **State Synchronization**
**Problem**: UI state and overlay state can get out of sync
**Solution**: Use central handler that updates both UI and overlay atomically

## Performance Considerations

### 1. **Render-Time Filtering**
- Element visibility is checked during each paint cycle
- Use efficient data structures (dictionaries/sets) for O(1) lookups
- Cache visibility state calculations when possible

### 2. **Memory Management**
- Store element references, not deep copies, when possible  
- Clean up path mappings when paths are deleted
- Use weak references if element lifecycle is managed elsewhere

### 3. **Update Efficiency**
```python
# Batch updates to avoid multiple repaints
self.drawing_overlay.blockSignals(True)
# ... multiple visibility changes
self.drawing_overlay.blockSignals(False)
self.drawing_overlay.update()  # Single repaint
```

## Extension Points

### 1. **Multiple Path Types**
```python
# Support different path categories
self.path_types = {
    'supply': {'color': 'blue', 'icon': '🔵'},
    'return': {'color': 'red', 'icon': '🔴'},
    'exhaust': {'color': 'gray', 'icon': '⚫'}
}
```

### 2. **Hierarchical Visibility**
```python
# Support nested path groups
self.path_hierarchy = {
    'system_1': ['path_1', 'path_2'],
    'system_2': ['path_3', 'path_4']
}
```

### 3. **Persistence**
```python
# Save/restore visibility state
def save_visibility_state(self):
    return {'visible_paths': list(self.visible_paths.keys())}

def restore_visibility_state(self, state):
    self.visible_paths.clear()
    for path_id in state.get('visible_paths', []):
        self.visible_paths[path_id] = True
```

## Conclusion

This pattern provides a robust, scalable approach to selective element visibility in Qt drawing applications. The key success factors are:

1. **Separation of data storage and UI controls**
2. **Multiple activation mechanisms for reliability** 
3. **Position-based element matching for robustness**
4. **Immediate visual feedback and state updates**
5. **Comprehensive fallback strategies**

The pattern is particularly valuable for complex drawing applications where users need granular control over element visibility, such as CAD tools, architectural drawings, or engineering diagrams.

## Implementation Status

- ✅ **Core Pattern**: Element mapping and conditional rendering
- ✅ **UI Controls**: Toggle buttons with visual feedback  
- ✅ **State Management**: Centralized visibility state
- ✅ **Registration System**: Dynamic element-to-path mapping
- ✅ **Fallback Mechanisms**: Multiple activation paths
- ✅ **Testing**: Component and integration test patterns
- ✅ **Production Ready**: Deployed and tested in acoustic analysis tool