## HVAC Path Persistence Debugging Summary

Summary of issues, diagnostics, and fixes related to retaining segment geometry when creating and editing HVAC Paths from the drawing UI.

### Problem
- Path segments drawn on the canvas did not retain geometry (e.g., width/height), and UI loads sometimes showed 1x1 values.
- Calculations failed or used defaults because the persisted path/segment data diverged from the drawing view.

### Key Findings
- Early refresh in `HVACSegmentDialog` could update the in-memory segment with default/partial values before UI controls were populated.
- Creating a Path while editing could inadvertently re-run the drawing-based creation flow, bypassing user edits.
- Segment ordering was not always preserved on save, causing confusion between displayed order and persisted order.

### Implemented Changes
1. Segment dialog guards
   - File: `src/ui/dialogs/hvac_segment_dialog.py`
   - Added `_ui_ready` guard so in-memory updates only occur after UI values are loaded.
   - Ensured `load_segment_data()` sets `_ui_ready = True` before refresh.
   - Added explicit debug statements (`DEBUG_SEG_*`) logging UI state and in-memory updates.

2. Preserve edits on Update Path
   - File: `src/ui/dialogs/hvac_path_dialog.py`
   - Changed `save_path()` to only use drawing-based creation when NOT editing.
   - On edit, persist current `segment_order` for existing segments without re-creating from drawing data.
   - Added `DEBUG_UI` logs around ordering updates.

3. Path data build and noise calc resiliency
   - File: `src/calculations/hvac_path_calculator.py`
   - Use fallback `noise_level` when source octave bands are missing.
   - When creating components from drawing, set default `noise_level` to allow immediate calculations.

### How to Verify
1. Enable debug: `HVAC_DEBUG_EXPORT=1`
2. Draw a path and save.
3. Open the path and edit a segment; change width/height, save segment, then click "Update Path".
4. Observe logs:
   - `DEBUG_SEG_SAVE` shows DB update and verification of geometry.
   - `DEBUG_UI` shows segment ordering updates (when applicable).
5. Re-open the segment; controls should reflect the saved geometry.

### Remaining Notes
- Validation errors like "Path project ID mismatch" and missing mechanical unit linkage are logged and do not block geometry persistence.
- The ASCII diagram now reflects `w x h` and shape from the in-memory list, consistent with DB after update.


