# Summary: Non-Modal Component Library Window

## What Changed

The **Component Library** dialog is now an independent, non-modal window that allows users to interact with other windows while it's open, and implements a singleton pattern to prevent multiple instances.

## Benefits

✅ **Persistent Reference Panel** - Keep library open as reference while working
✅ **Side-by-side workflow** - View component data alongside space/path editors
✅ **Singleton Pattern** - Only one library window at a time, brings to front if already open
✅ **Real-time Updates** - Changes automatically sync to parent window
✅ **Multi-tasking** - Switch between windows freely without reopening library
✅ **Better Productivity** - Seamless workflow for referencing mechanical units, silencers, and material schedules

## Files Modified

1. **src/ui/dialogs/component_library_dialog.py**
   - Removed modal flag (`setModal(False)`)
   - Added `Qt.Window` flag for independent window behavior
   - Added `library_updated` signal
   - Signal emitted after all data modifications (add/edit/delete/import)

2. **src/ui/project_dashboard.py**
   - Added `component_library_dialog` attribute for singleton reference
   - Changed from `exec()` to `show()` for dialog display
   - Added singleton check - brings existing window to front instead of creating new one
   - Added lifecycle management methods
   - Auto-refreshes data when library is updated

## How It Works Now

1. Click "Component Library" in the Project Dashboard
2. Dialog opens as a separate, independent window (not modal)
3. You can now:
   - Click anywhere in the main window
   - Edit spaces while referencing mechanical units
   - Set up HVAC paths while viewing silencer data
   - Compare material schedules across drawing sets
   - Position the library window beside other windows
   - Continue working while library stays open
4. Click "Component Library" again → brings existing window to front (singleton)
5. Make changes in library → parent window automatically refreshes
6. Close when done → reference removed for cleanup

## Key Features

### Singleton Pattern
```
First click: Opens Component Library window
Second click: Brings existing window to front (no duplicate)
Third click: Still just brings existing window to front
```

This prevents clutter and confusion from multiple library windows.

### Real-Time Synchronization
```
User adds mechanical unit in library
    ↓
library_updated signal emitted
    ↓
ProjectDashboard refreshes component data
    ↓
All views show updated data immediately
```

### Independent Window Management
- Can be positioned anywhere on screen
- Can be minimized/maximized independently
- Shows in taskbar as separate window
- User controls z-order (front/back)
- Doesn't force "always on top"

## Common Workflows

### Workflow 1: Equipment Setup
1. Open Component Library
2. Import mechanical schedule from PDF
3. Review imported units
4. Keep library open
5. Switch to Edit Space Properties
6. Reference equipment data while setting up room
7. Switch to HVAC Path dialog
8. Reference same equipment for path setup
9. Close library when done

### Workflow 2: Material Schedule Reference
```
┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐
│ Drawing PDF          │  │ Component Library    │  │ Edit Space Props   │
│                      │  │                      │  │                    │
│ [Material Schedule]  │  │ Acoustic Treatment   │  │ Room: Conf A       │
│                      │  │                      │  │                    │
│ Wall: Type GWB-01    │  │ Schedule: DD Phase   │  │ Ceiling Material:  │
│ NRC: 0.05            │◄─┼─► GWB-01: NRC 0.05  │◄─┼─► [Select: GWB-01] │
│                      │  │                      │  │                    │
│ Ceiling: ACT-75      │  │ Schedule: CD Phase   │  │ Wall Material:     │
│ NRC: 0.75            │  │ ACT-75: NRC 0.75     │  │ [Select: ACT-75]   │
└──────────────────────┘  └──────────────────────┘  └────────────────────┘

All three windows accessible simultaneously!
```

### Workflow 3: Silencer Database
1. Open Component Library → Silencers tab
2. Load silencer manufacturer PDF
3. Import IL values for multiple silencer models
4. Keep library open
5. Switch to HVAC Path dialog
6. Add segments and select silencers from library
7. Reference IL values while configuring path
8. Library stays open for quick reference

## Testing

Run the test to verify the behavior:
```bash
python test_non_modal_component_library.py
```

The test demonstrates:
1. Opening the library as a non-modal window
2. Interacting with both windows simultaneously
3. Singleton pattern (clicking button again brings window to front)
4. Signal updates (update counter increments when library changes)
5. Proper cleanup when window closes

## Technical Details

### Window Independence
- **Type**: Non-modal dialog with `Qt.Window` flag
- **Lifecycle**: Singleton pattern - only one instance allowed
- **Memory**: Reference stored in `component_library_dialog`, cleaned up on close
- **Signals**: `library_updated` for data changes, `finished` for cleanup

### Nested Dialogs
The Component Library contains several **modal** nested dialogs:
- Edit Mechanical Unit
- Edit Silencer
- Add Material Schedule
- Compare Schedules

These remain modal (blocking their parent Component Library) which is correct design - you shouldn't be able to edit the library list while an individual item's edit dialog is open.

### Signal Emission Points
The `library_updated` signal is emitted after:
- Adding/editing/deleting mechanical units
- Adding/editing/deleting silencers
- Saving frequency or IL values
- Importing from image or PDF
- Adding/editing/deleting material schedules

## Comparison: Before vs After

| Aspect | Before (Modal) | After (Non-Modal) |
|--------|----------------|-------------------|
| Window Type | Modal dialog | Independent window |
| Interaction | Blocks all other windows | Free interaction everywhere |
| Multiple Opens | Creates new dialog each time | Singleton - brings to front |
| Reference | Must close to work elsewhere | Stays open as reference |
| Updates | Manual refresh after close | Automatic real-time sync |
| Positioning | Limited | Free positioning anywhere |
| Multi-Monitor | Single monitor only | Can move to secondary monitor |
| Workflow | Interrupts task flow | Seamless integration |

## Use Cases

### Perfect For:
- 📋 **Equipment Reference** - Keep specs visible while designing
- 🔧 **HVAC Setup** - Reference components while building paths
- 🎨 **Material Selection** - Compare schedules across drawing phases
- 📊 **Data Import** - Import and immediately use without reopening
- 🖥️ **Multi-Monitor** - Library on one screen, work on another
- 📚 **Persistent Reference** - Library as reference panel throughout session

### Not Suitable For:
- Quick one-off lookups (but still works fine)
- Users who prefer modal dialogs (could add preference toggle in future)

## Documentation

See detailed technical documentation in:
- `NON_MODAL_COMPONENT_LIBRARY.md` - Complete technical documentation
- `test_non_modal_component_library.py` - Test script with verification

## No Breaking Changes

This is a UX enhancement only - all existing functionality remains intact. The Component Library works exactly the same way functionally, it's just no longer blocking other windows.

## Future Enhancements

Potential additions:
1. Remember window position/size between sessions
2. Keyboard shortcut to toggle library (e.g., Ctrl+L)
3. "Pin on Top" option for persistent visibility
4. Search/filter that persists across sessions
5. Sync highlighting between library and active component in main window
6. Quick-access toolbar for frequently used components

