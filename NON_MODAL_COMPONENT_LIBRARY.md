# Non-Modal Component Library Dialog

## Overview

The Component Library dialog has been converted from a modal dialog to a non-modal (independent) window. This allows users to keep the Component Library open while working with other parts of the application, enabling workflows such as:

- Referencing mechanical unit specifications while editing space properties
- Viewing silencer data while setting up HVAC paths
- Comparing acoustic treatment schedules with space materials
- Managing components while referencing drawing specifications
- Keeping the library open as a persistent reference panel

## Changes Made

### 1. ComponentLibraryDialog (`src/ui/dialogs/component_library_dialog.py`)

**Key Changes:**
- Changed `setModal(True)` to `setModal(False)` to make the dialog non-modal
- Added `Qt.Window` flag to make it behave as an independent window
- Added `library_updated` signal to notify parent when data changes
- Signal emitted after any create, update, delete, or import operation

**Signal:**
```python
library_updated = Signal()
```

This signal is emitted whenever:
- Mechanical units are added, edited, or deleted
- Silencers are added, edited, or deleted
- Frequency/IL values are saved
- Schedules are imported (from image or PDF)
- Material schedules are added, edited, or deleted

### 2. ProjectDashboard (`src/ui/project_dashboard.py`)

**Key Changes:**
- Added `component_library_dialog` attribute to store dialog reference
- Changed from using `dialog.exec()` (modal) to `dialog.show()` (non-modal)
- Added singleton pattern - if dialog is already open, brings it to front instead of creating a new one
- Added `on_component_library_updated()` method to refresh data when library changes
- Added `on_component_library_closed()` method to clean up dialog reference
- Connected dialog signals for proper lifecycle management

**Dialog Lifecycle:**
1. User clicks "Component Library" button
2. If dialog already exists and is visible, bring to front and return
3. Otherwise, create new dialog and show with `show()` instead of `exec()`
4. Dialog reference is stored in `component_library_dialog`
5. When user makes changes, `library_updated` signal triggers data refresh
6. When dialog closes, `finished` signal triggers cleanup

## User Experience

### Before (Modal)
- User clicks "Component Library"
- Dialog opens and blocks all other windows
- User must close dialog to work with other features
- Cannot reference library while editing spaces or paths

### After (Non-Modal)
- User clicks "Component Library"
- Dialog opens as independent window
- User can interact with main application, spaces, paths, etc.
- Dialog can be positioned side-by-side with other windows
- Clicking "Component Library" again brings existing window to front (singleton)
- Changes are saved immediately and parent UI updates automatically
- Dialog can remain open as persistent reference

## Key Features

### Singleton Pattern
Only one Component Library window can be open at a time. Clicking the "Component Library" button when one is already open will:
- Bring the existing window to the front
- Activate the window (focus it)
- Not create a duplicate window

This prevents clutter and confusion from multiple library windows.

### Real-Time Updates
When data is modified in the Component Library:
1. Changes are saved to the database immediately
2. `library_updated` signal is emitted
3. Parent window automatically refreshes its data
4. Other open windows see the updated data

### Window Independence
The Component Library window:
- Can be positioned anywhere on screen
- Can be minimized/maximized independently
- Appears as separate window in taskbar
- Can be placed behind or in front of other windows as needed
- Doesn't force "always on top" behavior

## Use Cases

### 1. Reference While Editing Spaces
```
┌────────────────────────┐  ┌────────────────────────┐
│ Edit Space Properties  │  │ Component Library      │
│                        │  │                        │
│ Room: Conference A     │  │ AHU-1: 2000 CFM       │
│                        │  │ Inlet:  78/85/92...    │
│ Select noise source:   │  │ Outlet: 72/78/85...    │
│ [AHU-1 from library]◄──┼──┤                        │
│                        │  │ RF-1: 500 CFM          │
│ Materials:             │  │                        │
│ - Ceiling: ACT         │  │ Silencers:             │
│ - Walls: GWB           │  │ - Model XYZ-24         │
└────────────────────────┘  │   IL: 15/20/25 dB      │
                            └────────────────────────┘
```

### 2. Import and Apply Workflow
1. Open Component Library
2. Import mechanical schedule from PDF
3. Review imported units in library
4. Switch to HVAC Path dialog
5. Reference library data while setting up path
6. Library stays open throughout process

### 3. Material Schedule Reference
1. Open Component Library → Acoustic Treatment tab
2. View material schedules from various drawing sets
3. Switch to Edit Space Properties
4. Apply materials based on schedule reference
5. Compare schedules side-by-side with space editor

## Technical Implementation

### Window Flags
The dialog uses `Qt.Window` flag, which:
- Makes it appear as a separate window in the taskbar
- Allows it to be minimized/maximized independently
- Enables free arrangement on screen
- Does not force it to stay on top

### Memory Management
- Single dialog reference stored in `component_library_dialog`
- Reference is set to `None` when dialog closes via `finished` signal
- Singleton pattern prevents multiple instances from accumulating
- Automatic cleanup on dialog close

### Signal Flow
```
User modifies library data
    ↓
Operation completes (add/edit/delete/import)
    ↓
Emit library_updated signal
    ↓
ProjectDashboard.on_component_library_updated()
    ↓
Refresh component library display
```

## Nested Dialog Handling

The Component Library contains several nested modal dialogs:
- `MechanicalUnitEditDialog` - Edit individual mechanical units
- `SilencerEditDialog` - Edit silencer products
- `ManualMechanicalUnitAddDialog` - Manual component entry
- `MaterialScheduleDialog` - Add/edit material schedules
- `MaterialScheduleComparisonDialog` - Compare schedules

These remain **modal** (as they should be) because they are editing dialogs that need to block interaction with the parent Component Library until the edit is complete. This is the correct design pattern.

## Compatibility

This change is backward compatible and does not require database migrations or changes to existing data structures. The Component Library can still be opened from:
- Project Dashboard
- HVAC Path Dialog
- Drawing Interface (if integrated in future)

## Future Enhancements

Potential improvements for this feature:
1. Remember window position/size between sessions
2. Add keyboard shortcut to toggle library visibility
3. Show indicator when library is open and has unsaved changes
4. Add "pin on top" option for users who want persistent visibility
5. Sync selection between library and main window (highlight active component)
6. Add search/filter that persists across sessions

## Benefits

✅ **Persistent Reference** - Keep library open while working on other tasks
✅ **Better Workflow** - No need to repeatedly open/close library
✅ **Side-by-Side Comparison** - View library data alongside space/path editors
✅ **Reduced Clicks** - Access library data without navigation interruption
✅ **Multi-Monitor Friendly** - Position library on secondary monitor
✅ **Improved Productivity** - Seamless workflow between library and main app

